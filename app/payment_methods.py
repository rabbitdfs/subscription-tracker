from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import PaymentMethod, Subscription, User

router = APIRouter(prefix="/api/payment-methods", tags=["Карты"])


class CardCreate(BaseModel):
    name: str
    kind: Literal["rub_card", "foreign_card"]
    markup_percent: Decimal = Decimal("0")


class CardUpdate(BaseModel):
    name: str | None = None
    markup_percent: Decimal | None = None


def check_card(card: PaymentMethod):
    if not card.name:
        raise HTTPException(status_code=422, detail="Укажите название карты")
    if not 0 <= card.markup_percent <= 100:
        raise HTTPException(status_code=422, detail="Комиссия должна быть от 0 до 100 процентов")


def get_own_card(card_id: int, user: User, db: Session) -> PaymentMethod:
    card = db.get(PaymentMethod, card_id)
    if card is None or card.user_id != user.id:
        raise HTTPException(status_code=404, detail="Карта не найдена")
    return card


def card_to_dict(card: PaymentMethod) -> dict:
    return {
        "id": card.id,
        "name": card.name,
        "kind": card.kind,
        "markup_percent": card.markup_percent,
    }


@router.get("")
def list_cards(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cards = db.scalars(
        select(PaymentMethod).where(PaymentMethod.user_id == user.id).order_by(PaymentMethod.id)
    )
    return [card_to_dict(card) for card in cards]


@router.post("", status_code=201)
def create_card(
    data: CardCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    card = PaymentMethod(
        user_id=user.id,
        name=data.name.strip(),
        kind=data.kind,
        # У российской карты комиссии нет
        markup_percent=data.markup_percent if data.kind == "foreign_card" else Decimal("0"),
    )
    check_card(card)
    db.add(card)
    db.commit()
    return card_to_dict(card)


@router.patch("/{card_id}")
def update_card(
    card_id: int,
    data: CardUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = get_own_card(card_id, user, db)
    if data.name is not None:
        card.name = data.name.strip()
    if data.markup_percent is not None and card.kind == "foreign_card":
        card.markup_percent = data.markup_percent
    check_card(card)
    db.commit()
    return card_to_dict(card)


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    card = get_own_card(card_id, user, db)
    # Карту, к которой привязаны подписки, удалять нельзя
    has_subscriptions = db.scalar(
        select(Subscription.id)
        .where(Subscription.payment_method_id == card.id, Subscription.deleted_at.is_(None))
        .limit(1)
    )
    if has_subscriptions:
        raise HTTPException(
            status_code=409, detail="К карте привязаны подписки, сначала удалите их или перенесите"
        )
    db.delete(card)
    db.commit()
