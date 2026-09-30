from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, new_csrf_token, verify_password
from app.dependencies.auth import CurrentUser, CsrfUser, DbSession
from app.models.entities import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, UserOut

router = APIRouter(prefix="/auth", tags=["Autenticação"])
limiter = Limiter(key_func=get_remote_address)


def set_auth_cookies(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie("access_token", token, max_age=max_age, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
    set_csrf_cookie(response)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    settings = get_settings()
    csrf_token = token or new_csrf_token()
    response.set_cookie("csrf_token", csrf_token, max_age=settings.access_token_expire_minutes * 60, httponly=False, secure=settings.cookie_secure, samesite="lax", path="/")
    return csrf_token


@router.post("/login", response_model=UserOut)
@limiter.limit("5/minute")
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    set_auth_cookies(response, create_access_token(user.id, user.role.value))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("csrf_token", path="/")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.get("/csrf")
def refresh_csrf(response: Response, user: CurrentUser):
    """Issue a fresh double-submit CSRF cookie for the current browser session."""
    return {"csrf_token": set_csrf_cookie(response)}


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: ChangePasswordRequest, user: CsrfUser, db: DbSession):
    if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual inválida")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
