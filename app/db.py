import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base, Operator, Setting, Tariff
from .security import hash_password

log = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Delivery times, editable from the admin panel → "Narxlar va muddatlar"
DEFAULT_SETTINGS = {
    "avia_pack_days": "3-6",
    "avia_transit_days": "6-12",
    "fura_pack_days": "",
    "fura_transit_days": "",
}


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
        has_admin = await s.scalar(select(Operator).where(Operator.role == "admin").limit(1))
        if not has_admin:
            s.add(Operator(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                full_name="Administrator",
                role="admin",
            ))
            log.warning("Admin account created: %s (change the password!)", settings.ADMIN_USERNAME)
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
