import logging
import time

from app import rates
from app.db import SessionLocal
from app.models import Rate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")


def save_rate(source: str, currency: str, value):
    with SessionLocal() as db:
        db.add(Rate(source=source, currency=currency, rate_to_rub=value))
        db.commit()
    log.info("Сохранен курс %s %s: %s", source, currency, value)


def update_usdt():
    try:
        save_rate("coingecko", "USDT", rates.fetch_usdt_rub())
    except Exception as error:
        log.error("Не удалось обновить курс USDT: %s", error)


def update_cbr():
    try:
        for currency, value in rates.fetch_cbr_rates().items():
            save_rate("cbr", currency, value)
    except Exception as error:
        log.error("Не удалось обновить курсы ЦБ: %s", error)


def main():
    log.info("Фоновая задача запущена")
    hour = 0
    while True:
        # Курс USDT каждый час, курсы ЦБ раз в сутки
        update_usdt()
        if hour % 24 == 0:
            update_cbr()
        hour += 1
        time.sleep(3600)


if __name__ == "__main__":
    main()
