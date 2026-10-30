import logging
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base, Operator, Setting, Tariff
from .security import hash_password

log = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=settings.DB_CONNECT_ARGS)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Delivery times, editable from the admin panel → "Narxlar va muddatlar"
DEFAULT_SETTINGS = {
    "avia_pack_days": "3-6",
    "avia_transit_days": "6-12",
    "fura_pack_days": "",
    "fura_transit_days": "",
}


async def _ensure_admin(s: AsyncSession) -> None:
    """Creates the first admin, or resets its password when ADMIN_RESET is set."""
    has_admin = await s.scalar(select(Operator).where(Operator.role == "admin").limit(1))
    if has_admin and not settings.ADMIN_RESET:
        return
    password = settings.ADMIN_PASSWORD
    if not password:
        if has_admin:
            log.error("ADMIN_RESET is set but ADMIN_PASSWORD is empty — nothing changed")
            return
        password = secrets.token_urlsafe(9)
        log.warning("ADMIN_PASSWORD is not set. Generated admin password: %s", password)

    op = await s.scalar(select(Operator).where(Operator.username == settings.ADMIN_USERNAME))
    if not op:
        op = Operator(username=settings.ADMIN_USERNAME, full_name="Administrator")
        s.add(op)
    op.password_hash = hash_password(password)
    op.role = "admin"
    op.is_active = True
    if has_admin:
        log.warning("Admin password was reset for '%s'. Remove ADMIN_RESET now.", settings.ADMIN_USERNAME)
    else:
        log.warning("Admin account created: %s", settings.ADMIN_USERNAME)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
        await _ensure_admin(s)
        old = {r.key: r for r in (await s.scalars(select(Setting))).all()}
        for key, value in DEFAULT_SETTINGS.items():
            if key not in old:
                s.add(Setting(key=key, value=value))

        # First start only: create price lines (older installs kept prices in settings)
        if "tariffs_seeded" not in old:
            s.add(Setting(key="tariffs_seeded", value="1"))
            for kind, p, default in (("AVIA", "avia", "10"), ("FURA", "fura", "")):
                price = old[f"{p}_price"].value if f"{p}_price" in old else default
                min_w = old[f"{p}_min_weight"].value if f"{p}_min_weight" in old else ("0.1" if kind == "AVIA" else "")
                try:
                    s.add(Tariff(kind=kind, price=float(price), unit="kg",
                                 min_amount=float(min_w) if min_w else None))
                except ValueError:
                    pass  # empty price → nothing to add
        for key in ("avia_price", "avia_min_weight", "fura_price", "fura_min_weight"):
            if key in old:
                await s.delete(old[key])
        await s.commit()
