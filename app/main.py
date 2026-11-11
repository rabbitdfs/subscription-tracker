import logging
import time

from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="Subscription Tracker")


# В лог пишем каждый запрос: метод, адрес, код ответа и за сколько миллисекунд ответили
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    log.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code, ms)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
