import asyncio
import io
import time
import math
from pathlib import Path
from urllib.parse import urlencode

import barcode
from barcode.writer import SVGWriter
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from starlette.middleware.sessions import SessionMiddleware

from ..config import settings
from ..db import DEFAULT_SETTINGS, SessionLocal
from ..models import Cargo, Client, Operator, Setting, StatusHistory, Tariff, utcnow
from ..security import hash_password, verify_password
from ..services import (
    BOT_STATUS, add_history, assign_tracking, client_by_phone, get_bot, normalize_phone, get_tariffs, normalize_tracking, notify_tracking, parse_client_code, set_status,
)
from ..export import cargos_xlsx, full_xlsx
from ..statuses import (
    AT_CHINA, BADGE, EXTRAS, KINDS, ORDER, ROLES, WAITING, can, can_set, label, next_status, op_kinds, op_targets,
    parse_perms,
)
from ..texts import num, price_line
from .i18n import tr

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=HERE / "templates")
PAGE_SIZE = 50


class LoginRequired(Exception):
    pass


class Forbidden(Exception):
    pass


def create_app() -> FastAPI:
    app = FastAPI(title="Dragon Life Cargo", docs_url=None, redoc_url=None, openapi_url=None)
    # max_age=None → the login cookie is deleted when the browser is closed.
    # On an https host (Render) the cookie is never sent over plain http.
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=None, same_site="lax",
                       https_only=settings.WEBHOOK_BASE.startswith("https://"))

    @app.middleware("http")
    async def _no_cache_pages(request: Request, call_next):
        # After logout the browser "Back" button must not show cached panel pages
        response = await call_next(request)
        if response.headers.get("content-type", "").startswith(("text/html", "application/json")):
            response.headers["Cache-Control"] = "no-store"
        return response
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc):
        return RedirectResponse("/login?expired=1" if exc.args and exc.args[0] == "expired" else "/login", status_code=303)

    @app.exception_handler(Forbidden)
    async def _forbidden(request: Request, exc):
        flash(request, tr(lang(request), "no_access"), "error")
        return RedirectResponse("/", status_code=303)

    _routes(app)
    return app


# ---------------- helpers ----------------

def lang(request: Request) -> str:
    return request.session.get("lang", "uz")


def flash(request: Request, msg: str, kind: str = "ok") -> None:
    request.session.setdefault("flash", []).append([kind, msg])


def _logout(request: Request) -> None:
    lg = request.session.get("lang")
    request.session.clear()
    if lg:
        request.session["lang"] = lg


async def session_operator(request: Request, s, touch: bool = True) -> tuple[Operator | None, bool]:
    """Logged-in operator, or (None, expired?). touch=False for background checks that are not user activity."""
    op_id = request.session.get("op")
    if not op_id:
        return None, False
    now = time.time()
    seen = request.session.get("seen", 0)
    started = request.session.get("login_at", 0)
    if now - seen > settings.SESSION_IDLE_MINUTES * 60 or now - started > settings.SESSION_MAX_HOURS * 3600:
        _logout(request)
        return None, True
    op = await s.get(Operator, op_id)
    if not op or not op.is_active:
        _logout(request)
        return None, False
    if touch:
        request.session["seen"] = int(now)
    return op, False


async def current(request: Request, s, admin: bool = False) -> Operator:
    op, expired = await session_operator(request, s)
    if not op:
        raise LoginRequired("expired" if expired else "")
    if admin and op.role != "admin":
        raise Forbidden()
    return op


def render(request: Request, name: str, op: Operator | None = None, **ctx):
    lg = lang(request)
    live = request.headers.get("X-Live") == "1"
    messages = [] if live else request.session.pop("flash", [])
    return templates.TemplateResponse(request, name, {
        "op": op, "lang": lg, "t": lambda k: tr(lg, k), "flashes": messages,
        "label": lambda st: label(st, lg), "BADGE": BADGE, "ORDER": ORDER, "ROLES": ROLES,
        "role_name": lambda r: ROLES.get(r, {}).get(lg, r), "can_set": can_set, "next_status": next_status,
        "can": can, "op_kinds": op_kinds, "op_targets": op_targets, "KINDS": KINDS, "EXTRAS": EXTRAS,
        **ctx,
    })


def back(request: Request, default: str = "/") -> RedirectResponse:
    ref = request.headers.get("referer") or default
    return RedirectResponse(ref, status_code=303)


async def load_cargo(s, cargo_id: int) -> Cargo | None:
    return await s.scalar(
        select(Cargo).where(Cargo.id == cargo_id)
        .options(selectinload(Cargo.client), selectinload(Cargo.history).selectinload(StatusHistory.operator))
    )


def search_filter(q: str):
    q = q.strip()
    conds = [Cargo.tracking_code.ilike(f"%{q.upper()}%"), Client.full_name.ilike(f"%{q}%"), Client.phone.ilike(f"%{q}%")]
    if parsed := parse_client_code(q):
        conds.append(Client.id == parsed[1])
    elif q.isdigit():
        conds.append(Client.id == int(q))
    return or_(*conds)


async def bot_info() -> dict:
    """What the admin sees in the "Bot holati" block."""
    info = {"token": BOT_STATUS["token"], "mode": BOT_STATUS["mode"], "error": BOT_STATUS["error"],
            "username": None, "hook_url": None, "pending": None, "last_error": None, "last_error_at": None}
    bot = get_bot()
    if not bot:
        return info
    try:
        me = await asyncio.wait_for(bot.get_me(), 10)
        info["username"] = me.username
        hook = await asyncio.wait_for(bot.get_webhook_info(), 10)
        info.update(hook_url=hook.url or None, pending=hook.pending_update_count,
                    last_error=hook.last_error_message, last_error_at=hook.last_error_date)
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def cargo_query(op: Operator, q: str, kind: str, status: str):
    """Cargo list filters shared by the dashboard and the Excel export."""
    kinds = op_kinds(op)
    base = select(Cargo).join(Client).where(Cargo.kind.in_(kinds))
    if q.strip():
        base = base.where(search_filter(q))
    if kind in kinds:
        base = base.where(Cargo.kind == kind)
    if status == "no_tracking":
        base = base.where(Cargo.tracking_code.is_(None))
    elif status == "active":
        base = base.where(Cargo.status.in_(ORDER[:-1]))
    elif status in ORDER:
        base = base.where(Cargo.status == status)
    return base


def xlsx_response(data: bytes, name: str) -> Response:
    filename = f"{name}_{utcnow():%Y-%m-%d_%H-%M}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def barcode_svg(code: str) -> bytes:
    buf = io.BytesIO()
    barcode.get("code128", code, writer=SVGWriter()).write(
        buf, options={"module_height": 15, "font_size": 8, "text_distance": 4, "quiet_zone": 4}
    )
    return buf.getvalue()


# ---------------- routes ----------------

def _routes(app: FastAPI) -> None:

    @app.get("/api/updates")
    async def updates(request: Request, since_id: int = 0):
        """Cheap check used by live.js every few seconds: has anything changed?"""
        async with SessionLocal() as s:
            op, expired = await session_operator(request, s, touch=False)  # polling is not activity
            if not op:
                return JSONResponse({"error": "expired" if expired else "login"}, status_code=401)
            kinds = op_kinds(op)
            last_id, changed, total = (await s.execute(
                select(func.max(Cargo.id), func.max(Cargo.updated_at), func.count(Cargo.id)).where(Cargo.kind.in_(kinds))
            )).one()
            last_client = await s.scalar(select(func.max(Client.id)))
            new_count = await s.scalar(
                select(func.count(Cargo.id)).where(Cargo.kind.in_(kinds), Cargo.id > since_id)
            ) if since_id else 0
        return JSONResponse({
            "last_id": last_id or 0, "changed": changed.isoformat() if changed else "", "total": total,
            "last_client": last_client or 0, "new_count": new_count,
        }, headers={"Cache-Control": "no-store"})

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.get("/lang/{code}")
    async def set_lang(request: Request, code: str):
        request.session["lang"] = code if code in ("uz", "ru") else "uz"
        return back(request)

    # ----- auth -----
    @app.get("/login")
    async def login_page(request: Request, expired: str = ""):
        if expired:
            flash(request, tr(lang(request), "session_expired"), "error")
        return render(request, "login.html")

    @app.post("/login")
    async def login(request: Request, username: str = Form(...), password: str = Form(...)):
        async with SessionLocal() as s:
            op = await s.scalar(select(Operator).where(Operator.username == username.strip()))
        if not op or not op.is_active or not verify_password(password, op.password_hash):
            flash(request, tr(lang(request), "bad_login"), "error")
            return RedirectResponse("/login", status_code=303)
        _logout(request)  # start from a clean session
        now = int(time.time())
        request.session.update(op=op.id, login_at=now, seen=now)
        return RedirectResponse("/", status_code=303)

    @app.get("/logout")
    async def logout(request: Request):
        _logout(request)
        return RedirectResponse("/login", status_code=303)

    # ----- cargo list -----
    @app.get("/")
    async def dashboard(request: Request, q: str = "", kind: str = "", status: str = "", page: int = 1):
        async with SessionLocal() as s:
            op = await current(request, s)
            kinds = op_kinds(op)
            base = cargo_query(op, q, kind, status)

            total = await s.scalar(select(func.count()).select_from(base.subquery()))
            pages = max(1, math.ceil(total / PAGE_SIZE))
            page = min(max(page, 1), pages)
            cargos = (await s.scalars(
                base.options(selectinload(Cargo.client)).order_by(Cargo.updated_at.desc())
                .offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
            )).all()

            counts = dict((await s.execute(
                select(Cargo.status, func.count()).where(Cargo.kind.in_(kinds)).group_by(Cargo.status)
            )).all())
            no_track = await s.scalar(
                select(func.count()).select_from(Cargo).where(Cargo.kind.in_(kinds), Cargo.tracking_code.is_(None))
            )
        qs = lambda p: "?" + urlencode({"q": q, "kind": kind, "status": status, "page": p})
        return render(request, "dashboard.html", op, cargos=cargos, q=q, kind=kind, status=status, kinds=kinds,
                      counts=counts, no_track=no_track, total=total, page=page, pages=pages, qs=qs,
                      export_qs=urlencode({"q": q, "kind": kind, "status": status}),
                      targets=op_targets(op))

    # ----- cargo actions -----
    @app.post("/cargo/{cargo_id}/generate")
    async def cargo_generate(request: Request, cargo_id: int):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
            if cargo and cargo.kind in op_kinds(op) and not cargo.tracking_code:
                await assign_tracking(s, cargo, op)
                flash(request, f"{tr(lang(request), 'tracking_generated')}: {cargo.tracking_code}")
        return back(request)

    @app.post("/cargo/{cargo_id}/status")
    async def cargo_status(request: Request, cargo_id: int, status: str = Form(...), next_url: str = Form("")):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
            if not cargo or status not in ORDER or not can_set(op, cargo.kind, status):
                flash(request, tr(lang(request), "no_rights"), "error")
            elif await set_status(s, cargo, status, op):
                flash(request, f"{tr(lang(request), 'status_changed')}: {cargo.tracking_code or cargo.id} → {label(status, lang(request))}")
        if next_url.startswith("/"):
            return RedirectResponse(next_url, status_code=303)
        return back(request)

    @app.get("/cargo/{cargo_id}")
    async def cargo_detail(request: Request, cargo_id: int):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
        if not cargo or cargo.kind not in op_kinds(op):
            return RedirectResponse("/", status_code=303)
        return render(request, "cargo.html", op, cargo=cargo, targets=op_targets(op))

    @app.post("/cargo/{cargo_id}/edit")
    async def cargo_edit(request: Request, cargo_id: int, weight_kg: str = Form(""), note: str = Form("")):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
            if cargo and cargo.kind in op_kinds(op):
                try:
                    cargo.weight_kg = float(weight_kg.replace(",", ".")) if weight_kg.strip() else None
                except ValueError:
                    pass
                cargo.note = note.strip() or None
                cargo.updated_at = utcnow()
                await s.commit()
                flash(request, tr(lang(request), "saved"))
        return back(request)

    @app.post("/cargo/{cargo_id}/delete")
    async def cargo_delete(request: Request, cargo_id: int):
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            cargo = await load_cargo(s, cargo_id)
            if cargo:
                await s.delete(cargo)
                await s.commit()
                flash(request, tr(lang(request), "deleted"))
        return RedirectResponse("/", status_code=303)

    # ----- barcode -----
    @app.get("/barcode/{code}.svg")
    async def barcode_image(request: Request, code: str):
        async with SessionLocal() as s:
            await current(request, s)
        return Response(barcode_svg(code), media_type="image/svg+xml")

    @app.get("/cargo/{cargo_id}/label")
    async def cargo_label(request: Request, cargo_id: int):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
        if not cargo or not cargo.tracking_code or cargo.kind not in op_kinds(op):
            return RedirectResponse("/", status_code=303)
        return render(request, "label.html", op, cargo=cargo, now=utcnow())

    # ----- scan -----
    @app.get("/scan")
    async def scan(request: Request, code: str = ""):
        cargo, normalized = None, ""
        async with SessionLocal() as s:
            op = await current(request, s)
            if code.strip():
                normalized = normalize_tracking(code) or code.strip().upper()
                cargo = await s.scalar(select(Cargo).where(Cargo.tracking_code == normalized))
                if cargo:
                    cargo = await load_cargo(s, cargo.id)
        allowed = []
        if cargo:
            allowed = [st for st in ORDER if st != cargo.status and can_set(op, cargo.kind, st)]
        suggested = None
        if cargo and (nxt := next_status(cargo.status)) and nxt in allowed:
            suggested = nxt
        return render(request, "scan.html", op, code=normalized, cargo=cargo, allowed=allowed, suggested=suggested)

    # ----- new cargo -----
    @app.get("/cargo-new")
    async def cargo_new_page(request: Request, tracking: str = "", client_code: str = "", new_client: str = "",
                             new_name: str = "", new_phone: str = "", new_kind: str = ""):
        async with SessionLocal() as s:
            op = await current(request, s)
            if not can(op, "add"):
                raise Forbidden()
        return render(request, "cargo_new.html", op, tracking=tracking, client_code=client_code,
                      statuses=[st for st in op_targets(op)], default_status=AT_CHINA,
                      kinds=op_kinds(op), new_client=new_client == "1", new_name=new_name,
                      new_phone=new_phone, new_kind=new_kind)

    @app.get("/api/client")
    async def client_lookup(request: Request, code: str = ""):
        """Shows the client's name under the code field while the operator types."""
        async with SessionLocal() as s:
            op = await current(request, s)
            parsed = parse_client_code(code)
            client = await s.get(Client, parsed[1]) if parsed else None
        if not client or parsed[0] not in op_kinds(op):
            return JSONResponse({"found": False})
        return JSONResponse({"found": True, "name": client.full_name, "phone": client.phone,
                             "code": client.code(parsed[0]), "telegram": bool(client.telegram_id)})

    @app.post("/cargo-new")
    async def cargo_new(request: Request, client_code: str = Form(""), tracking: str = Form(""),
                        status: str = Form(WAITING), weight_kg: str = Form(""), note: str = Form(""),
                        new_client: str = Form(""), new_name: str = Form(""), new_phone: str = Form(""),
                        new_kind: str = Form("")):
        lg = lang(request)
        async with SessionLocal() as s:
            op = await current(request, s)
            if not can(op, "add"):
                raise Forbidden()
            redirect_back = RedirectResponse("/cargo-new?" + urlencode({
                "tracking": tracking, "client_code": client_code, "new_client": new_client,
                "new_name": new_name, "new_phone": new_phone, "new_kind": new_kind}), 303)

            if new_client == "1":
                # New client typed in by the operator: permanent code is created automatically
                name = " ".join(new_name.split())
                phone = normalize_phone(new_phone)
                kind = new_kind if new_kind in op_kinds(op) else None
                if not 2 <= len(name) <= 64 or not phone or not kind:
                    flash(request, tr(lg, "bad_new_client"), "error")
                    return redirect_back
                client = await client_by_phone(s, phone)
                if client:
                    client_msg = f"{tr(lg, 'client_exists')}: {client.code(kind)} — {client.full_name}"
                else:
                    client = Client(full_name=name, phone=phone, lang="uz")
                    s.add(client)
                    await s.flush()
                    client_msg = f"{tr(lg, 'client_created')}: {client.avia_code} / {client.fura_code} — {name}"
            else:
                client_msg = None
                parsed = parse_client_code(client_code)
                client = await s.get(Client, parsed[1]) if parsed else None
                if not client or parsed[0] not in op_kinds(op):
                    flash(request, tr(lg, "bad_client_code"), "error")
                    return redirect_back
                kind = parsed[0]
            code = None
            if tracking.strip():
                code = normalize_tracking(tracking)
                if not code:
                    flash(request, tr(lg, "bad_tracking"), "error")
                    return redirect_back
                if await s.scalar(select(Cargo.id).where(Cargo.tracking_code == code)):
                    flash(request, tr(lg, "tracking_exists"), "error")
                    return redirect_back
            if status not in ORDER or not can_set(op, kind, status):
                status = WAITING
            try:
                weight = float(weight_kg.replace(",", ".")) if weight_kg.strip() else None
            except ValueError:
                weight = None
            cargo = Cargo(client_id=client.id, kind=kind, tracking_code=code, status=status,
                          weight_kg=weight, note=note.strip() or None)
            s.add(cargo)
            await s.flush()
            await add_history(s, cargo, status, op, comment="Operator qo'shdi")
            await s.commit()
            cargo = await load_cargo(s, cargo.id)
            if not code:
                await assign_tracking(s, cargo, op)  # also notifies the client
            else:
                await notify_tracking(cargo)
        if client_msg:
            flash(request, client_msg)
        flash(request, f"{tr(lg, 'cargo_created')}: {cargo.tracking_code}")
        return RedirectResponse(f"/cargo/{cargo.id}", status_code=303)

    # ----- clients -----
    @app.get("/clients")
    async def clients(request: Request, q: str = "", page: int = 1):
        async with SessionLocal() as s:
            op = await current(request, s)
            base = select(Client)
            if q.strip():
                conds = [Client.full_name.ilike(f"%{q}%"), Client.phone.ilike(f"%{q}%"), Client.username.ilike(f"%{q}%")]
                if parsed := parse_client_code(q):
                    conds.append(Client.id == parsed[1])
                elif q.strip().isdigit():
                    conds.append(Client.id == int(q))
                base = base.where(or_(*conds))
            total = await s.scalar(select(func.count()).select_from(base.subquery()))
            pages = max(1, math.ceil(total / PAGE_SIZE))
            page = min(max(page, 1), pages)
            rows = (await s.scalars(base.order_by(Client.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))).all()
            counts = dict((await s.execute(
                select(Cargo.client_id, func.count()).where(Cargo.client_id.in_([c.id for c in rows])).group_by(Cargo.client_id)
            )).all()) if rows else {}
        qs = lambda p: "?" + urlencode({"q": q, "page": p})
        return render(request, "clients.html", op, clients=rows, q=q, total=total, page=page, pages=pages, qs=qs, counts=counts)

    @app.get("/clients/{client_id}")
    async def client_detail(request: Request, client_id: int):
        async with SessionLocal() as s:
            op = await current(request, s)
            client = await s.get(Client, client_id)
            if not client:
                return RedirectResponse("/clients", status_code=303)
            cargos = (await s.scalars(
                select(Cargo).where(Cargo.client_id == client_id, Cargo.kind.in_(op_kinds(op)))
                .options(selectinload(Cargo.client)).order_by(Cargo.updated_at.desc())
            )).all()
        return render(request, "client.html", op, client=client, cargos=cargos)

    # ----- admin: operators -----
    @app.get("/admin/operators")
    async def operators(request: Request):
        async with SessionLocal() as s:
            op = await current(request, s, admin=True)
            ops = (await s.scalars(select(Operator).order_by(Operator.id))).all()
        return render(request, "operators.html", op, operators=ops)

    def _perms_from_form(form) -> str:
        return ",".join(parse_perms(",".join(form.getlist("perm"))))

    @app.post("/admin/operators")
    async def operator_add(request: Request):
        form = await request.form()
        lg = lang(request)
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
        role = "admin" if form.get("role") == "admin" else "operator"
        permissions = _perms_from_form(form)
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            if not username or len(password) < 4:
                flash(request, tr(lg, "fill_required"), "error")
            elif role == "operator" and not any(k in permissions.split(",") for k in KINDS):
                flash(request, tr(lg, "need_direction"), "error")
            elif await s.scalar(select(Operator.id).where(Operator.username == username)):
                flash(request, tr(lg, "username_taken"), "error")
            else:
                s.add(Operator(username=username, password_hash=hash_password(password),
                               full_name=str(form.get("full_name", "")).strip(), role=role,
                               permissions="" if role == "admin" else permissions))
                await s.commit()
                flash(request, f"{tr(lg, 'saved')}: {username}")
        return RedirectResponse("/admin/operators", status_code=303)

    @app.post("/admin/operators/{op_id}")
    async def operator_edit(request: Request, op_id: int):
        form = await request.form()
        lg = lang(request)
        async with SessionLocal() as s:
            me = await current(request, s, admin=True)
            target = await s.get(Operator, op_id)
            if not target:
                return RedirectResponse("/admin/operators", status_code=303)
            password = str(form.get("password", ""))
            if password and len(password) < 4:
                flash(request, tr(lg, "fill_required"), "error")
                return RedirectResponse("/admin/operators", status_code=303)
            target.full_name = str(form.get("full_name", "")).strip()
            if target.id != me.id:  # an admin cannot lock themselves out
                role = "admin" if form.get("role") == "admin" else "operator"
                permissions = _perms_from_form(form)
                if role == "operator" and not any(k in permissions.split(",") for k in KINDS):
                    flash(request, tr(lg, "need_direction"), "error")
                    return RedirectResponse("/admin/operators", status_code=303)
                target.role = role
                target.permissions = "" if role == "admin" else permissions
                target.is_active = bool(form.get("is_active"))
            if password:
                target.password_hash = hash_password(password)
            await s.commit()
            flash(request, f"{tr(lg, 'saved')}: {target.username}")
        return RedirectResponse("/admin/operators", status_code=303)

    # ----- Excel export -----
    @app.get("/export/cargos.xlsx")
    async def export_cargos(request: Request, q: str = "", kind: str = "", status: str = ""):
        async with SessionLocal() as s:
            op = await current(request, s)
            if not can(op, "export"):
                raise Forbidden()
            cargos = (await s.scalars(
                cargo_query(op, q, kind, status).options(selectinload(Cargo.client)).order_by(Cargo.updated_at.desc())
            )).all()
        return xlsx_response(cargos_xlsx(list(cargos), lang(request)), "dragonlife_yuklar")

    @app.get("/admin/export.xlsx")
    async def export_all(request: Request):
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            clients = (await s.scalars(select(Client).order_by(Client.id))).all()
            cargos = (await s.scalars(select(Cargo).options(selectinload(Cargo.client)).order_by(Cargo.id))).all()
            history = (await s.scalars(select(StatusHistory).options(
                selectinload(StatusHistory.operator), selectinload(StatusHistory.cargo)).order_by(StatusHistory.id))).all()
            tariffs = await get_tariffs(s, active_only=False)
        data = full_xlsx(list(clients), list(cargos), list(history), tariffs, lang(request))
        return xlsx_response(data, "dragonlife_baza")

    # ----- admin: bot status & export -----
    @app.get("/admin/settings")
    async def settings_page(request: Request):
        async with SessionLocal() as s:
            op = await current(request, s, admin=True)
        return render(request, "settings.html", op, bot=await bot_info())

    @app.post("/admin/bot/reconnect")
    async def bot_reconnect(request: Request):
        async with SessionLocal() as s:
            await current(request, s, admin=True)
        bot = get_bot()
        try:
            if not bot or BOT_STATUS.get("mode") != "webhook":
                raise RuntimeError("bot / webhook is off")
            await bot.set_webhook(BOT_STATUS["webhook_url"], secret_token=BOT_STATUS["secret"],
                                  allowed_updates=BOT_STATUS.get("allowed_updates"), drop_pending_updates=True)
            BOT_STATUS["error"] = None
            flash(request, tr(lang(request), "saved"))
        except Exception as e:
            flash(request, f"{type(e).__name__}: {e}", "error")
        return RedirectResponse("/admin/settings", status_code=303)

    # ----- admin: prices & delivery times -----
    @app.get("/admin/prices")
    async def prices_page(request: Request):
        async with SessionLocal() as s:
            op = await current(request, s, admin=True)
            values = {r.key: r.value for r in (await s.scalars(select(Setting))).all()}
            tariffs = await get_tariffs(s, active_only=False)
        by_kind = {k: [x for x in tariffs if x.kind == k] for k in ("AVIA", "FURA")}
        preview = {k: [price_line(x, lang(request)) for x in v if x.is_active] for k, v in by_kind.items()}
        return render(request, "prices.html", op, values=values, by_kind=by_kind, preview=preview, num=num)

    @app.post("/admin/prices/days")
    async def days_save(request: Request):
        form = await request.form()
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            for key in DEFAULT_SETTINGS:
                if key in form:
                    row = await s.get(Setting, key) or Setting(key=key)
                    row.value = str(form[key]).strip()
                    s.add(row)
            await s.commit()
        flash(request, tr(lang(request), "saved"))
        return RedirectResponse("/admin/prices", status_code=303)

    def _read_tariff(form) -> dict | None:
        def f(name):
            raw = str(form.get(name, "")).strip().replace(",", ".")
            return float(raw) if raw else None
        try:
            price, min_amount = f("price"), f("min_amount")
            sort = int(str(form.get("sort", "0")).strip() or 0)
        except ValueError:
            return None
        if price is None or price < 0 or (min_amount is not None and min_amount < 0):
            return None
        return {
            "title_uz": str(form.get("title_uz", "")).strip()[:128],
            "title_ru": str(form.get("title_ru", "")).strip()[:128],
            "price": price, "min_amount": min_amount, "sort": sort,
            "unit": form.get("unit") if form.get("unit") in ("kg", "m3", "piece") else "kg",
            "currency": (str(form.get("currency", "USD")).strip().upper() or "USD")[:8],
            "is_active": bool(form.get("is_active")),
        }

    @app.post("/admin/prices")
    async def tariff_add(request: Request):
        form = await request.form()
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            data = _read_tariff(form)
            kind = form.get("kind")
            if not data or kind not in ("AVIA", "FURA"):
                flash(request, tr(lang(request), "bad_price"), "error")
            else:
                data["is_active"] = True
                s.add(Tariff(kind=kind, **data))
                await s.commit()
                flash(request, tr(lang(request), "saved"))
        return RedirectResponse("/admin/prices", status_code=303)

    @app.post("/admin/prices/{tariff_id}")
    async def tariff_edit(request: Request, tariff_id: int):
        form = await request.form()
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            tariff = await s.get(Tariff, tariff_id)
            data = _read_tariff(form)
            if not tariff or not data:
                flash(request, tr(lang(request), "bad_price"), "error")
            else:
                for k, v in data.items():
                    setattr(tariff, k, v)
                await s.commit()
                flash(request, tr(lang(request), "saved"))
        return RedirectResponse("/admin/prices", status_code=303)

    @app.post("/admin/prices/{tariff_id}/delete")
    async def tariff_delete(request: Request, tariff_id: int):
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            tariff = await s.get(Tariff, tariff_id)
            if tariff:
                await s.delete(tariff)
                await s.commit()
                flash(request, tr(lang(request), "deleted"))
        return RedirectResponse("/admin/prices", status_code=303)
