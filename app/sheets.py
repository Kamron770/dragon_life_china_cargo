"""Copies the database into Google Sheets (one-way backup, refreshed after every change)."""
import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .config import BASE_DIR, settings

log = logging.getLogger(__name__)

_dirty = asyncio.Event()


def enabled() -> bool:
    return bool(settings.GOOGLE_CREDENTIALS_FILE and settings.GOOGLE_SHEET_ID)


def mark_dirty() -> None:
    _dirty.set()


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


async def _collect() -> dict[str, list[list]]:
    from .db import SessionLocal
    from .models import Cargo, Client, StatusHistory
    from .statuses import label

    async with SessionLocal() as s:
        clients = (await s.scalars(select(Client).order_by(Client.id))).all()
        cargos = (await s.scalars(select(Cargo).options(selectinload(Cargo.client)).order_by(Cargo.id))).all()
        history = (await s.scalars(
            select(StatusHistory).options(selectinload(StatusHistory.operator)).order_by(StatusHistory.id)
        )).all()

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
    }


def _write(data: dict[str, list[list]]) -> None:
    import gspread

    cred = Path(settings.GOOGLE_CREDENTIALS_FILE)
    if not cred.is_absolute():
        cred = BASE_DIR / cred
    gc = gspread.service_account(filename=str(cred))
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
    await asyncio.to_thread(_write, data)
    log.info("Google Sheets synced")


async def sync_loop() -> None:
    if not enabled():
        log.info("Google Sheets backup is off (GOOGLE_CREDENTIALS_FILE / GOOGLE_SHEET_ID not set)")
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
