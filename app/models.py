from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Client(Base):
    """A bot user. `id` is also the permanent client number: A001 / F001."""

    __tablename__ = "clients"
    __table_args__ = {"sqlite_autoincrement": True}  # never reuse numbers

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lang: Mapped[str] = mapped_column(String(2), default="uz")
    full_name: Mapped[str] = mapped_column(String(128), default="")
    phone: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    cargos: Mapped[list["Cargo"]] = relationship(back_populates="client")

    @property
    def avia_code(self) -> str:
        return f"A{self.id:03d}"

    @property
    def fura_code(self) -> str:
        return f"F{self.id:03d}"

    def code(self, kind: str) -> str:
        return self.avia_code if kind == "AVIA" else self.fura_code


class Cargo(Base):
    __tablename__ = "cargos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    kind: Mapped[str] = mapped_column(String(8))  # AVIA | FURA
    tracking_code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    tracking_auto: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), index=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    client: Mapped[Client] = relationship(back_populates="cargos")
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="cargo", order_by="StatusHistory.id", cascade="all, delete-orphan"
    )

    @property
    def client_code(self) -> str:
        return self.client.code(self.kind)


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cargo_id: Mapped[int] = mapped_column(ForeignKey("cargos.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    cargo: Mapped[Cargo] = relationship(back_populates="history")
    operator: Mapped["Operator | None"] = relationship()


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[str] = mapped_column(String(32))  # admin | china_avia | china_fura | uzbekistan
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
