import io
import math
from pathlib import Path
from urllib.parse import urlencode

import barcode
from barcode.writer import SVGWriter
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from starlette.middleware.sessions import SessionMiddleware

from .. import sheets
from ..config import settings
from ..db import DEFAULT_SETTINGS, SessionLocal
from ..models import Cargo, Client, Operator, Setting, StatusHistory, utcnow
from ..security import hash_password, verify_password
from ..services import (
    add_history, assign_tracking, normalize_tracking, notify_tracking, parse_client_code, set_status,
)
from ..statuses import AT_CHINA, BADGE, ORDER, ROLES, WAITING, can_set, label, next_status, role_kinds, role_targets
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
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, max_age=60 * 60 * 24 * 14, same_site="lax")
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc):
        return RedirectResponse("/login", status_code=303)

    @app.exception_handler(Forbidden)
    async def _forbidden(request: Request, exc):
        flash(request, tr(lang(request), "only_admin"), "error")
        return RedirectResponse("/", status_code=303)

    _routes(app)
    return app


# ---------------- helpers ----------------

def lang(request: Request) -> str:
    return request.session.get("lang", "uz")


def flash(request: Request, msg: str, kind: str = "ok") -> None:
    request.session.setdefault("flash", []).append([kind, msg])


async def current(request: Request, s, admin: bool = False) -> Operator:
    op_id = request.session.get("op")
    op = await s.get(Operator, op_id) if op_id else None
    if not op or not op.is_active:
        request.session.pop("op", None)
        raise LoginRequired()
    if admin and op.role != "admin":
        raise Forbidden()
    return op


def render(request: Request, name: str, op: Operator | None = None, **ctx):
    lg = lang(request)
    messages = request.session.pop("flash", [])
    return templates.TemplateResponse(request, name, {
        "op": op, "lang": lg, "t": lambda k: tr(lg, k), "flashes": messages,
        "label": lambda st: label(st, lg), "BADGE": BADGE, "ORDER": ORDER, "ROLES": ROLES,
        "role_name": lambda r: ROLES.get(r, {}).get(lg, r), "can_set": can_set, "next_status": next_status,
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


def barcode_svg(code: str) -> bytes:
    buf = io.BytesIO()
    barcode.get("code128", code, writer=SVGWriter()).write(
        buf, options={"module_height": 15, "font_size": 8, "text_distance": 4, "quiet_zone": 4}
    )
    return buf.getvalue()


# ---------------- routes ----------------

def _routes(app: FastAPI) -> None:

    @app.get("/lang/{code}")
    async def set_lang(request: Request, code: str):
        request.session["lang"] = code if code in ("uz", "ru") else "uz"
        return back(request)

    # ----- auth -----
    @app.get("/login")
    async def login_page(request: Request):
        return render(request, "login.html")

    @app.post("/login")
    async def login(request: Request, username: str = Form(...), password: str = Form(...)):
        async with SessionLocal() as s:
            op = await s.scalar(select(Operator).where(Operator.username == username.strip()))
        if not op or not op.is_active or not verify_password(password, op.password_hash):
            flash(request, tr(lang(request), "bad_login"), "error")
            return RedirectResponse("/login", status_code=303)
        request.session["op"] = op.id
        return RedirectResponse("/", status_code=303)

    @app.get("/logout")
    async def logout(request: Request):
        request.session.pop("op", None)
        return RedirectResponse("/login", status_code=303)

    # ----- cargo list -----
    @app.get("/")
    async def dashboard(request: Request, q: str = "", kind: str = "", status: str = "", page: int = 1):
        async with SessionLocal() as s:
            op = await current(request, s)
            kinds = role_kinds(op.role)
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
                      targets=role_targets(op.role))

    # ----- cargo actions -----
    @app.post("/cargo/{cargo_id}/generate")
    async def cargo_generate(request: Request, cargo_id: int):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
            if cargo and cargo.kind in role_kinds(op.role) and not cargo.tracking_code:
                await assign_tracking(s, cargo, op)
                flash(request, f"{tr(lang(request), 'tracking_generated')}: {cargo.tracking_code}")
        return back(request)

    @app.post("/cargo/{cargo_id}/status")
    async def cargo_status(request: Request, cargo_id: int, status: str = Form(...), next_url: str = Form("")):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
            if not cargo or status not in ORDER or not can_set(op.role, cargo.kind, status):
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
        if not cargo or cargo.kind not in role_kinds(op.role):
            return RedirectResponse("/", status_code=303)
        return render(request, "cargo.html", op, cargo=cargo, targets=role_targets(op.role))

    @app.post("/cargo/{cargo_id}/edit")
    async def cargo_edit(request: Request, cargo_id: int, weight_kg: str = Form(""), note: str = Form("")):
        async with SessionLocal() as s:
            op = await current(request, s)
            cargo = await load_cargo(s, cargo_id)
            if cargo and cargo.kind in role_kinds(op.role):
                try:
                    cargo.weight_kg = float(weight_kg.replace(",", ".")) if weight_kg.strip() else None
                except ValueError:
                    pass
                cargo.note = note.strip() or None
                cargo.updated_at = utcnow()
                await s.commit()
                sheets.mark_dirty()
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
                sheets.mark_dirty()
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
        if not cargo or not cargo.tracking_code or cargo.kind not in role_kinds(op.role):
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
            allowed = [st for st in ORDER if st != cargo.status and can_set(op.role, cargo.kind, st)]
        suggested = None
        if cargo and (nxt := next_status(cargo.status)) and nxt in allowed:
            suggested = nxt
        return render(request, "scan.html", op, code=normalized, cargo=cargo, allowed=allowed, suggested=suggested)

    # ----- new cargo -----
    @app.get("/cargo-new")
    async def cargo_new_page(request: Request, tracking: str = "", client_code: str = ""):
        async with SessionLocal() as s:
            op = await current(request, s)
        return render(request, "cargo_new.html", op, tracking=tracking, client_code=client_code,
                      statuses=[st for st in role_targets(op.role)], default_status=AT_CHINA)

    @app.post("/cargo-new")
    async def cargo_new(request: Request, client_code: str = Form(...), tracking: str = Form(""),
                        status: str = Form(WAITING), weight_kg: str = Form(""), note: str = Form("")):
        lg = lang(request)
        async with SessionLocal() as s:
            op = await current(request, s)
            parsed = parse_client_code(client_code)
            client = await s.get(Client, parsed[1]) if parsed else None
            redirect_back = RedirectResponse("/cargo-new?" + urlencode({"tracking": tracking, "client_code": client_code}), 303)
            if not client or parsed[0] not in role_kinds(op.role):
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
            if status not in ORDER or not can_set(op.role, kind, status):
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
            sheets.mark_dirty()
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
                select(Cargo).where(Cargo.client_id == client_id, Cargo.kind.in_(role_kinds(op.role)))
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

    @app.post("/admin/operators")
    async def operator_add(request: Request, username: str = Form(""), password: str = Form(""),
                           full_name: str = Form(""), role: str = Form("")):
        lg = lang(request)
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            username = username.strip()
            if not username or len(password) < 4 or role not in ROLES:
                flash(request, tr(lg, "fill_required"), "error")
            elif await s.scalar(select(Operator.id).where(Operator.username == username)):
                flash(request, tr(lg, "username_taken"), "error")
            else:
                s.add(Operator(username=username, password_hash=hash_password(password),
                               full_name=full_name.strip(), role=role))
                await s.commit()
                flash(request, tr(lg, "saved"))
        return RedirectResponse("/admin/operators", status_code=303)

    @app.post("/admin/operators/{op_id}")
    async def operator_edit(request: Request, op_id: int, full_name: str = Form(""), role: str = Form(""),
                            password: str = Form(""), is_active: str = Form("")):
        async with SessionLocal() as s:
            me = await current(request, s, admin=True)
            target = await s.get(Operator, op_id)
            if target:
                target.full_name = full_name.strip()
                if role in ROLES and target.id != me.id:
                    target.role = role
                if target.id != me.id:
                    target.is_active = bool(is_active)
                if password:
                    if len(password) < 4:
                        flash(request, tr(lang(request), "fill_required"), "error")
                        return RedirectResponse("/admin/operators", status_code=303)
                    target.password_hash = hash_password(password)
                await s.commit()
                flash(request, tr(lang(request), "saved"))
        return RedirectResponse("/admin/operators", status_code=303)

    # ----- admin: settings -----
    @app.get("/admin/settings")
    async def settings_page(request: Request):
        async with SessionLocal() as s:
            op = await current(request, s, admin=True)
            values = {r.key: r.value for r in (await s.scalars(select(Setting))).all()}
        return render(request, "settings.html", op, values=values, sheets_on=sheets.enabled(),
                      sheet_id=settings.GOOGLE_SHEET_ID)

    @app.post("/admin/settings")
    async def settings_save(request: Request):
        form = await request.form()
        async with SessionLocal() as s:
            await current(request, s, admin=True)
            for key in DEFAULT_SETTINGS:
                if key in form:
                    row = await s.get(Setting, key) or Setting(key=key)
                    row.value = str(form[key]).strip().replace(",", ".") if "price" in key or "weight" in key else str(form[key]).strip()
                    s.add(row)
            await s.commit()
        flash(request, tr(lang(request), "saved"))
        return RedirectResponse("/admin/settings", status_code=303)

    @app.post("/admin/sync")
    async def sync(request: Request):
        async with SessionLocal() as s:
            await current(request, s, admin=True)
        try:
            await sheets.sync_now()
            flash(request, tr(lang(request), "synced"))
        except Exception as e:
            flash(request, f"Google Sheets: {e}", "error")
        return RedirectResponse("/admin/settings", status_code=303)
