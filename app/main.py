import logging
import os
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app import pages
from app import auth
from app import payment_methods, subscriptions
from app import pricing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="Subscription Tracker")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
# Cookie для входа, живет 30 дней
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=30 * 24 * 3600)

app.include_router(pages.router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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

app.include_router(auth.router)
app.include_router(pricing.router)

app.include_router(payment_methods.router)
app.include_router(subscriptions.router)
