import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["Регистрация и вход"])


class Credentials(BaseModel):
    email: str
    password: str


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Нужно войти")
    return user


@router.post("/register", status_code=201)
def register(data: Credentials, request: Request, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="Неправильная почта")
    if len(data.password) < 8:
        raise HTTPException(status_code=422, detail="Пароль должен быть не короче 8 символов")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Эта почта уже занята")

    # В базе храним только хеш пароля
    password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()

    # После регистрации пользователь сразу вошел: кладем его id в cookie
    request.session["user_id"] = user.id
    return {"id": user.id, "email": user.email}


@router.post("/login")
def login(data: Credentials, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if user is None or not bcrypt.checkpw(data.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Неверная почта или пароль")
    request.session["user_id"] = user.id
    return {"id": user.id, "email": user.email}


@router.post("/logout", status_code=204)
def logout(request: Request):
    request.session.clear()
