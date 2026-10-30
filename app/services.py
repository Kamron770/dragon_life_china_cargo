"""Business logic shared by the bot and the web panel."""
import html
import logging
import re
import secrets

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Cargo, Client, Operator, Setting, StatusHistory, Tariff, utcnow
from .statuses import label
from .texts import kind_name, t

log = logging.getLogger(__name__)

_bot: Bot | None = None
# Filled in main.py, shown on the admin "Bot holati" block
BOT_STATUS: dict = {"token": False, "mode": None, "error": None, "webhook_url": None}

TRACK_RE = re.compile(r"^[A-Z0-9\-]{5,40}$")
CLIENT_CODE_RE = re.compile(r"^([AF])0*(\d+)$")


def set_bot(bot: Bot | None) -> None:
    global _bot
    _bot = bot


def get_bot() -> Bot | None:
    return _bot


def normalize_tracking(raw: str) -> str | None:
    code = re.sub(r"\s+", "", raw or "").upper()
    return code if TRACK_RE.match(code) else None


def parse_client_code(raw: str) -> tuple[str, int] | None:
    """'A001' -> ('AVIA', 1), 'f12' -> ('FURA', 12)."""
    m = CLIENT_CODE_RE.match((raw or "").strip().upper())
    if not m:
        return None
    return ("AVIA" if m.group(1) == "A" else "FURA"), int(m.group(2))


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:  # 901234567 -> +998901234567
        digits = "998" + digits
    if not 9 <= len(digits) <= 15:
        return None
    return "+" + digits


async def get_settings(s: AsyncSession) -> dict[str, str]:
    rows = (await s.scalars(select(Setting))).all()
    return {r.key: r.value for r in rows}


async def get_tariffs(s: AsyncSession, kind: str | None = None, active_only: bool = True) -> list[Tariff]:
    q = select(Tariff).order_by(Tariff.kind, Tariff.sort, Tariff.id)
    if kind:
        q = q.where(Tariff.kind == kind)
    if active_only:
        q = q.where(Tariff.is_active.is_(True))
    return list((await s.scalars(q)).all())


async def generate_tracking(s: AsyncSession, kind: str) -> str:
    prefix = "DLA" if kind == "AVIA" else "DLF"
    while True:
        code = prefix + "".join(secrets.choice("0123456789") for _ in range(9))
        if not await s.scalar(select(Cargo.id).where(Cargo.tracking_code == code)):
            return code


async def add_history(s: AsyncSession, cargo: Cargo, status: str, operator: Operator | None, comment: str | None = None):
    s.add(StatusHistory(cargo_id=cargo.id, status=status,
                        operator_id=operator.id if operator else None, comment=comment))


async def set_status(s: AsyncSession, cargo: Cargo, status: str, operator: Operator | None) -> bool:
    """Change status, write history, commit and notify the client. Returns False if unchanged."""
    if cargo.status == status:
        return False
    cargo.status = status
    cargo.updated_at = utcnow()
    await add_history(s, cargo, status, operator)
    await s.commit()
    await notify_status(cargo)
    return True


async def assign_tracking(s: AsyncSession, cargo: Cargo, operator: Operator | None) -> str:
    cargo.tracking_code = await generate_tracking(s, cargo.kind)
    cargo.tracking_auto = True
    cargo.updated_at = utcnow()
    await add_history(s, cargo, cargo.status, operator, comment=f"Trek kod yaratildi: {cargo.tracking_code}")
    await s.commit()
    await notify_tracking(cargo)
    return cargo.tracking_code


async def _send(client: Client, text: str) -> None:
    if not _bot or not client.telegram_id:
        return
    try:
        await _bot.send_message(client.telegram_id, text)
    except Exception as e:  # user blocked the bot, etc.
        log.warning("Notify %s failed: %s", client.telegram_id, e)


async def notify_status(cargo: Cargo) -> None:
    c = cargo.client
    code = cargo.tracking_code or t("no_code", c.lang)
    await _send(c, t("notify_status", c.lang, kind=kind_name(cargo.kind, c.lang),
                     code=html.escape(code), status=label(cargo.status, c.lang)))


async def notify_tracking(cargo: Cargo) -> None:
    c = cargo.client
    await _send(c, t("notify_tracking", c.lang, kind=kind_name(cargo.kind, c.lang),
                     code=html.escape(cargo.tracking_code or ""), status=label(cargo.status, c.lang)))
