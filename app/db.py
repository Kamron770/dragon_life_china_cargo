import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base, Operator, Setting
from .security import hash_password

log = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Editable from the admin panel → "Sozlamalar"
DEFAULT_SETTINGS = {
    "avia_price": "10",
    "avia_min_weight": "0.1",
    "avia_pack_days": "3-6",
    "avia_transit_days": "6-12",
    "fura_price": "",
    "fura_min_weight": "",
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
        existing = set((await s.scalars(select(Setting.key))).all())
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                s.add(Setting(key=key, value=value))
        await s.commit()
