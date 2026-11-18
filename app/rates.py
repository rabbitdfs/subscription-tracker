import logging
import time
import xml.etree.ElementTree as ET
from decimal import Decimal

import httpx

log = logging.getLogger("rates")

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub"
CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


# Если сайт не ответил, пробуем еще 2 раза с паузой 5 секунд
def download(url: str) -> httpx.Response:
    for attempt in range(1, 4):
        try:
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            return response
        except httpx.HTTPError as error:
            log.warning("Попытка %d из 3: %s не ответил: %s", attempt, url, error)
            if attempt < 3:
                time.sleep(5)
    raise RuntimeError(f"Сайт не ответил после 3 попыток: {url}")


def fetch_usdt_rub() -> Decimal:
    data = download(COINGECKO_URL).json()
    return Decimal(str(data["tether"]["rub"]))


def fetch_cbr_rates() -> dict[str, Decimal]:
    root = ET.fromstring(download(CBR_URL).content)
    result = {}
    for valute in root.findall("Valute"):
        code = valute.findtext("CharCode")
        if code in ("USD", "EUR"):
            # У ЦБ дробная часть через запятую, а курс бывает указан за 10 или 100 единиц
            value = Decimal(valute.findtext("Value").replace(",", "."))
            nominal = Decimal(valute.findtext("Nominal"))
            result[code] = value / nominal
    if "USD" not in result:
        raise RuntimeError("В ответе ЦБ нет курса доллара")
    return result
