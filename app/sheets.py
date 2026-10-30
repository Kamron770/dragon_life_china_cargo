"""Copies the database into Google Sheets (one-way backup, refreshed after every change)."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .config import BASE_DIR, settings

log = logging.getLogger(__name__)

_dirty = asyncio.Event()
# Shown in the admin panel
STATUS: dict = {"last_ok": None, "error": None}


def _credentials() -> dict | None:
    if settings.GOOGLE_CREDENTIALS_JSON:
        # strict=False: accepts a key pasted with real line breaks inside private_key
        return json.loads(settings.GOOGLE_CREDENTIALS_JSON.strip(), strict=False)
    if settings.GOOGLE_CREDENTIALS_FILE:
        cred = Path(settings.GOOGLE_CREDENTIALS_FILE)
        if not cred.is_absolute():
            cred = BASE_DIR / cred
        return json.loads(cred.read_text(), strict=False)
    return None


def service_email() -> str | None:
    """The robot email the spreadsheet must be shared with."""
    try:
        return (_credentials() or {}).get("client_email")
    except Exception as e:
        STATUS["error"] = f"Google key (JSON) o'qilmadi: {e}"
        return None


def enabled() -> bool:
    return bool((settings.GOOGLE_CREDENTIALS_FILE or settings.GOOGLE_CREDENTIALS_JSON) and settings.GOOGLE_SHEET_ID)


def mark_dirty() -> None:
    _dirty.set()


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


async def _collect() -> dict[str, list[list]]:
    from .db import SessionLocal
    from .models import Cargo, Client, StatusHistory, Tariff
    from .statuses import label

    async with SessionLocal() as s:
        clients = (await s.scalars(select(Client).order_by(Client.id))).all()
        cargos = (await s.scalars(select(Cargo).options(selectinload(Cargo.client)).order_by(Cargo.id))).all()
        history = (await s.scalars(
            select(StatusHistory).options(selectinload(StatusHistory.operator)).order_by(StatusHistory.id)
        )).all()
        tariffs = (await s.scalars(select(Tariff).order_by(Tariff.kind, Tariff.sort, Tariff.id))).all()

    return {
        "Mijozlar": [["ID", "AVIA kodi", "FURA kodi", "Ism", "Telefon", "Telegram ID", "Username", "Til", "Ro'yxatdan o'tgan"]]
        + [[c.id, c.avia_code, c.fura_code, c.full_name, c.phone, str(c.telegram_id or ""), c.username or "",
            c.lang, _fmt(c.created_at)] for c in clients],
        "Yuklar": [["ID", "Mijoz kodi", "Ism", "Telefon", "Turi", "Trek kod", "Avto trek", "Holat", "Og'irlik (kg)",
                    "Izoh", "Yaratilgan", "Yangilangan"]]
        + [[g.id, g.client_code, g.client.full_name, g.client.phone, g.kind, g.tracking_code or "",
            "ha" if g.tracking_auto else "", label(g.status, "uz"), g.weight_kg or "", g.note or "",
            _fmt(g.created_at), _fmt(g.updated_at)] for g in cargos],
        "Tarix": [["ID", "Yuk ID", "Holat", "Operator", "Izoh", "Vaqt"]]
        + [[h.id, h.cargo_id, label(h.status, "uz"), h.operator.username if h.operator else "bot",
            h.comment or "", _fmt(h.created_at)] for h in history],
        "Narxlar": [["ID", "Turi", "Nomi (uz)", "Nomi (ru)", "Narx", "Valyuta", "Birlik", "Minimal", "Botda"]]
        + [[x.id, x.kind, x.title_uz, x.title_ru, x.price, x.currency, x.unit, x.min_amount or "",
            "ha" if x.is_active else "yo'q"] for x in tariffs],
    }


def _write(data: dict[str, list[list]]) -> None:
    import gspread

    gc = gspread.service_account_from_dict(_credentials())
    book = gc.open_by_key(settings.GOOGLE_SHEET_ID)
    existing = {ws.title: ws for ws in book.worksheets()}
    for title, rows in data.items():
        ws = existing.get(title) or book.add_worksheet(title=title, rows=max(len(rows), 100), cols=len(rows[0]))
        ws.clear()
        ws.update(values=rows, range_name="A1")
        ws.freeze(rows=1)


async def sync_now() -> None:
    if not enabled():
        return
    data = await _collect()
    try:
        await asyncio.to_thread(_write, data)
    except Exception as e:
        STATUS["error"] = _explain(e)
        raise
    STATUS.update(last_ok=datetime.now(timezone.utc), error=None)
    log.info("Google Sheets synced")


def _explain(e: Exception) -> str:
    text = f"{type(e).__name__}: {e}"
    if "PERMISSION_DENIED" in text or "403" in text:
        if "has not been used" in text or "disabled" in text:
            return text + " → Google Cloud'da Google Sheets API / Google Drive API yoqilmagan"
        return text + " → jadval robot email'iga Editor sifatida ulashilmagan"
    if "404" in text or "NOT_FOUND" in text:
        return text + " → GOOGLE_SHEET_ID noto'g'ri"
    return text


async def sync_loop() -> None:
    if not enabled():
        log.info("Google Sheets backup is off (GOOGLE_SHEET_ID or credentials not set)")
        return
    _dirty.set()  # full copy on start
    while True:
        await _dirty.wait()
        _dirty.clear()
        try:
            await sync_now()
        except Exception as e:
            log.exception("Google Sheets sync failed: %s", e)
            _dirty.set()
        await asyncio.sleep(settings.SHEETS_SYNC_INTERVAL)  # batch frequent changes
