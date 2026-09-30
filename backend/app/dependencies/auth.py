from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.entities import Role, User

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, access_token: str | None = Cookie(default=None)) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação obrigatória")
    payload = decode_access_token(access_token)
    user = db.get(User, int(payload["sub"]))
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo ou inexistente")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def verify_csrf(user: CurrentUser, csrf_cookie: str | None = Cookie(default=None, alias="csrf_token"), x_csrf_token: str | None = Header(default=None)) -> User:
    if not csrf_cookie or not x_csrf_token or csrf_cookie != x_csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Validação CSRF falhou")
    return user


CsrfUser = Annotated[User, Depends(verify_csrf)]
