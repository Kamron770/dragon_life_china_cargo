import logging
import secrets

from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base, Operator, Setting, Tariff
from .security import hash_password
from .statuses import LEGACY_ROLES

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


def _add_missing_columns(conn) -> None:
    """create_all() makes new tables but never changes existing ones: add new columns here."""
    insp = inspect(conn)
    for table, column, ddl in NEW_COLUMNS:
        if table in insp.get_table_names() and column not in {c["name"] for c in insp.get_columns(table)}:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            log.warning("Database: added column %s.%s", table, column)


# (table, column, SQL type) — columns added after the first release
NEW_COLUMNS = [
    ("operators", "permissions", "TEXT DEFAULT ''"),
]


async def _migrate_operator_roles(s: AsyncSession) -> None:
    """Old fixed roles (China AVIA / China FURA / Uzbekistan) → operator with the same rights ticked."""
    for op in (await s.scalars(select(Operator).where(Operator.role.in_(list(LEGACY_ROLES))))).all():
        op.permissions = ",".join(LEGACY_ROLES[op.role])
        op.role = "operator"
        log.warning("Operator %s moved to permissions: %s", op.username, op.permissions)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)

    async with SessionLocal() as s:
        await _ensure_admin(s)
        await _migrate_operator_roles(s)
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
