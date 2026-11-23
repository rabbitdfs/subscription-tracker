from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models import PaymentMethod, Rate, Subscription
from app.pricing import Rates, choose_rates, price_rub, totals

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)

# Доллар по 100 рублей, евро по 1,1 доллара: так результат легко проверить в уме
RATES = Rates(usd_rub=Decimal("100"), eur_usd=Decimal("1.1"), rate_date=NOW)
RUB_CARD = PaymentMethod(kind="rub_card", markup_percent=Decimal("0"))
FOREIGN_CARD = PaymentMethod(kind="foreign_card", markup_percent=Decimal("5"))


def make_subscription(amount_minor, currency, period="month"):
    return Subscription(amount_minor=amount_minor, currency=currency, period=period)


def make_rate(value, hours_ago):
    return Rate(rate_to_rub=Decimal(value), fetched_at=NOW - timedelta(hours=hours_ago))


def test_rub_price_stays_the_same():
    assert price_rub(make_subscription(29900, "RUB"), RUB_CARD, RATES) == Decimal("299.00")


def test_usd_price_includes_card_markup():
    # 20 долларов * 100 рублей * 1,05 = 2100 рублей
    assert price_rub(make_subscription(2000, "USD"), FOREIGN_CARD, RATES) == Decimal("2100.00")


def test_eur_price_goes_through_usd():
    # 10 евро = 11 долларов, 11 * 100 * 1,05 = 1155 рублей
    assert price_rub(make_subscription(1000, "EUR"), FOREIGN_CARD, RATES) == Decimal("1155.00")


def test_no_rate_gives_no_price():
    no_rates = Rates(usd_rub=None, eur_usd=None, rate_date=None)
    assert price_rub(make_subscription(2000, "USD"), FOREIGN_CARD, no_rates) is None


def test_year_subscription_is_twelfth_part_in_month():
    items = [
        (make_subscription(120000, "RUB", "year"), RUB_CARD),  # 1200 рублей в год
        (make_subscription(30000, "RUB"), RUB_CARD),  # 300 рублей в месяц
    ]
    month, year = totals(items, RATES)
    assert month == Decimal("400.00")  # 1200 / 12 + 300
    assert year == Decimal("4800.00")  # 1200 + 300 * 12


def test_fresh_usdt_is_used():
    rates = choose_rates(make_rate("95", 1), make_rate("90", 5), None, NOW)
    assert rates.usd_rub == Decimal("95")
    assert not rates.is_approx
    assert not rates.is_stale


def test_old_usdt_falls_back_to_cbr():
    rates = choose_rates(make_rate("95", 5), make_rate("90", 5), None, NOW)
    assert rates.usd_rub == Decimal("90")
    assert rates.is_approx


def test_all_rates_old_means_stale():
    rates = choose_rates(make_rate("95", 72), make_rate("90", 72), None, NOW)
    assert rates.usd_rub == Decimal("95")
    assert rates.is_stale
