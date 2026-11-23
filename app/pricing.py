from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import PaymentMethod, Rate, Subscription, User

router = APIRouter(prefix="/api", tags=["Расходы и курсы"])

USDT_MAX_AGE = timedelta(hours=3)
CBR_MAX_AGE = timedelta(days=2)
KOPECKS = Decimal("0.01")


@dataclass
class Rates:
    usd_rub: Decimal | None
    eur_usd: Decimal | None
    rate_date: datetime | None
    is_approx: bool = False
    is_stale: bool = False


def choose_rates(usdt: Rate | None, usd: Rate | None, eur: Rate | None, now: datetime) -> Rates:
    eur_usd = eur.rate_to_rub / usd.rate_to_rub if eur and usd else None

    # Свежий курс USDT: считаем по нему
    if usdt and now - usdt.fetched_at < USDT_MAX_AGE:
        return Rates(usdt.rate_to_rub, eur_usd, usdt.fetched_at)
    # USDT давно не обновлялся: считаем по доллару ЦБ, это примерно
    if usd and now - usd.fetched_at < CBR_MAX_AGE:
        return Rates(usd.rate_to_rub, eur_usd, usd.fetched_at, is_approx=True)
    # Свежих курсов нет: берем последний сохраненный и пишем, что курс устарел
    if usdt:
        return Rates(usdt.rate_to_rub, eur_usd, usdt.fetched_at, is_stale=True)
    if usd:
        return Rates(usd.rate_to_rub, eur_usd, usd.fetched_at, is_approx=True, is_stale=True)
    return Rates(None, None, None)


def latest_rate(db: Session, source: str, currency: str) -> Rate | None:
    return db.scalar(
        select(Rate)
        .where(Rate.source == source, Rate.currency == currency)
        .order_by(Rate.fetched_at.desc())
        .limit(1)
    )


def get_rates(db: Session) -> Rates:
    return choose_rates(
        latest_rate(db, "coingecko", "USDT"),
        latest_rate(db, "cbr", "USD"),
        latest_rate(db, "cbr", "EUR"),
        datetime.now(timezone.utc),
    )


def price_rub(subscription: Subscription, card: PaymentMethod, rates: Rates) -> Decimal | None:
    amount = Decimal(subscription.amount_minor) / 100
    if subscription.currency == "RUB":
        return amount.quantize(KOPECKS)
    if rates.usd_rub is None:
        return None
    if subscription.currency == "EUR":
        if rates.eur_usd is None:
            return None
        # Евро сначала переводим в доллары по курсам ЦБ
        amount = amount * rates.eur_usd
    rub = amount * rates.usd_rub * (1 + card.markup_percent / 100)
    return rub.quantize(KOPECKS, ROUND_HALF_UP)


def totals(items, rates: Rates) -> tuple[Decimal, Decimal]:
    month = Decimal("0")
    year = Decimal("0")
    for subscription, card in items:
        price = price_rub(subscription, card, rates)
        if price is None:
            continue
        # Годовая подписка в месяц стоит 1/12 своей цены
        if subscription.period == "year":
            month += price / 12
            year += price
        else:
            month += price
            year += price * 12
    return month.quantize(KOPECKS, ROUND_HALF_UP), year.quantize(KOPECKS, ROUND_HALF_UP)


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.execute(
        select(Subscription, PaymentMethod)
        .join(PaymentMethod, Subscription.payment_method_id == PaymentMethod.id)
        .where(
            Subscription.user_id == user.id,
            Subscription.is_active.is_(True),
            Subscription.deleted_at.is_(None),
        )
    ).all()
    rates = get_rates(db)
    month, year = totals(items, rates)
    return {
        "month_total_rub": month,
        "year_total_rub": year,
        "active_count": len(items),
        "rate_date": rates.rate_date,
        "is_approx": rates.is_approx,
        "is_stale": rates.is_stale,
    }


@router.get("/rates")
def current_rates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = {}
    for source, currency in [("coingecko", "USDT"), ("cbr", "USD"), ("cbr", "EUR")]:
        rate = latest_rate(db, source, currency)
        if rate is None:
            result[currency] = None
        else:
            result[currency] = {"rate_to_rub": rate.rate_to_rub, "fetched_at": rate.fetched_at}
    return result
