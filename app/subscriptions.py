from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import PaymentMethod, Subscription, User
from app.payment_methods import get_own_card
from app.pricing import get_rates, price_rub

router = APIRouter(prefix="/api/subscriptions", tags=["Подписки"])


class SubscriptionCreate(BaseModel):
    name: str
    url: str | None = None
    amount: Decimal
    currency: Literal["RUB", "USD", "EUR"]
    period: Literal["month", "year"]
    next_charge_date: date
    payment_method_id: int


class SubscriptionUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    amount: Decimal | None = None
    currency: Literal["RUB", "USD", "EUR"] | None = None
    period: Literal["month", "year"] | None = None
    next_charge_date: date | None = None
    payment_method_id: int | None = None
    is_active: bool | None = None


def check_subscription(sub: Subscription, card: PaymentMethod):
    if not sub.name:
        raise HTTPException(status_code=422, detail="Укажите название подписки")
    if sub.amount_minor <= 0:
        raise HTTPException(status_code=422, detail="Цена должна быть больше нуля")
    if sub.url and not sub.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="Ссылка должна начинаться с http:// или https://")
    if card.kind == "rub_card" and sub.currency != "RUB":
        raise HTTPException(
            status_code=422, detail="Российской картой можно оплатить только подписку в рублях"
        )
    if card.kind == "foreign_card" and sub.currency == "RUB":
        raise HTTPException(
            status_code=422,
            detail="Иностранной картой можно оплатить только подписку в долларах или евро",
        )


def get_own_subscription(sub_id: int, user: User, db: Session) -> Subscription:
    sub = db.get(Subscription, sub_id)
    if sub is None or sub.user_id != user.id or sub.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    return sub


def subscription_to_dict(sub: Subscription, card: PaymentMethod, rates) -> dict:
    return {
        "id": sub.id,
        "name": sub.name,
        "url": sub.url,
        "amount": Decimal(sub.amount_minor) / 100,
        "currency": sub.currency,
        "period": sub.period,
        "next_charge_date": sub.next_charge_date,
        "payment_method_id": sub.payment_method_id,
        "is_active": sub.is_active,
        "price_rub": price_rub(sub, card, rates),
        "rate_date": rates.rate_date,
        "rate_is_approx": rates.is_approx,
    }


@router.get("")
def list_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Subscription, PaymentMethod)
        .join(PaymentMethod, Subscription.payment_method_id == PaymentMethod.id)
        .where(Subscription.user_id == user.id, Subscription.deleted_at.is_(None))
        .order_by(Subscription.next_charge_date)
    ).all()
    rates = get_rates(db)
    return [subscription_to_dict(sub, card, rates) for sub, card in rows]


@router.post("", status_code=201)
def create_subscription(
    data: SubscriptionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    card = get_own_card(data.payment_method_id, user, db)
    sub = Subscription(
        user_id=user.id,
        payment_method_id=card.id,
        name=data.name.strip(),
        url=data.url or None,
        # В базе цена в копейках (центах)
        amount_minor=int(data.amount * 100),
        currency=data.currency,
        period=data.period,
        next_charge_date=data.next_charge_date,
        is_active=True,
    )
    check_subscription(sub, card)
    db.add(sub)
    db.commit()
    return subscription_to_dict(sub, card, get_rates(db))


@router.patch("/{sub_id}")
def update_subscription(
    sub_id: int,
    data: SubscriptionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = get_own_subscription(sub_id, user, db)
    # Меняем только те поля, которые прислали
    if data.name is not None:
        sub.name = data.name.strip()
    if data.url is not None:
        sub.url = data.url or None
    if data.amount is not None:
        sub.amount_minor = int(data.amount * 100)
    if data.currency is not None:
        sub.currency = data.currency
    if data.period is not None:
        sub.period = data.period
    if data.next_charge_date is not None:
        sub.next_charge_date = data.next_charge_date
    if data.payment_method_id is not None:
        sub.payment_method_id = data.payment_method_id
    if data.is_active is not None:
        sub.is_active = data.is_active

    card = get_own_card(sub.payment_method_id, user, db)
    check_subscription(sub, card)
    db.commit()
    return subscription_to_dict(sub, card, get_rates(db))


@router.delete("/{sub_id}", status_code=204)
def delete_subscription(
    sub_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    sub = get_own_subscription(sub_id, user, db)
    # Не стираем, а помечаем удаленной, чтобы осталась история списаний
    sub.deleted_at = datetime.now(timezone.utc)
    db.commit()
