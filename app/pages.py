
# HTML-страницы приложения
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

# Роутер для HTML-страниц
router = APIRouter(include_in_schema=False)

# Папка, в которой будут находиться HTML-шаблоны
templates = Jinja2Templates(
    directory=Path(__file__).parent / "templates"
)


@router.get("/")
def index_page(request: Request):
    # Если пользователь не авторизован,
    # перенаправляем его на страницу входа
    if not request.session.get("user_id"):
        return RedirectResponse("/login")

    return templates.TemplateResponse(request, "index.html")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")
