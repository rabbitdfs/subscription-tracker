from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    # Комиссия сервиса пополнения в процентах, у российской карты 0
    markup_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    # Индекс только по активным и не удаленным подпискам, по нему ищем ближайшие списания
    __table_args__ = (
        Index(
            "ix_subscriptions_next_charge_date",
            "next_charge_date",
            postgresql_where=text("is_active AND deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    # Если карту удалят, у старых удаленных подписок тут станет пусто
    payment_method_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("payment_methods.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(String(500))
    # Цена в копейках или центах: целые числа не дают ошибок округления
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(4))
    period: Mapped[str] = mapped_column(String(10))
    next_charge_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Rate(Base):
    __tablename__ = "rates"
    __table_args__ = (
        Index("ix_rates_source_currency_fetched_at", "source", "currency", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(4))
    rate_to_rub: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Charge(Base):
    __tablename__ = "charges"
    __table_args__ = (
        Index("ix_charges_subscription_id_charge_date", "subscription_id", "charge_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subscriptions.id"))
    charge_date: Mapped[date] = mapped_column(Date)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(4))
    rate_to_rub: Mapped[Decimal] = mapped_column(Numeric(14, 6))
    rub_amount_minor: Mapped[int] = mapped_column(BigInteger)
    is_approx: Mapped[bool] = mapped_column(default=False)
