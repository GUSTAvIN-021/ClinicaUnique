from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, new_csrf_token, verify_password
from app.dependencies.auth import CurrentUser, CsrfUser, DbSession
from app.models.entities import User
from app.schemas.auth import ChangePasswordRequest, CurrentPasswordRequest, LoginRequest, TotpCodeRequest, UserOut
from app.services.audit import record_audit

import pyotp
import base64
from io import BytesIO
import qrcode

router = APIRouter(prefix="/auth", tags=["Autenticação"])
limiter = Limiter(key_func=get_remote_address)


def set_auth_cookies(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie("access_token", token, max_age=max_age, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/")
    set_csrf_cookie(response)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    settings = get_settings()
    csrf_token = token or new_csrf_token()
    response.set_cookie("csrf_token", csrf_token, max_age=settings.access_token_expire_minutes * 60, httponly=False, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/")
    return csrf_token


@router.post("/login", response_model=UserOut)
@limiter.limit("5/minute")
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        record_audit(db, actor=None, action="auth.login_failed", resource_type="session", resource_id="unknown")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if user.mfa_enabled:
        code = (payload.totp_code or "").replace(" ", "")
        if not code or not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1):
            record_audit(db, actor=user, action="auth.mfa_failed", resource_type="session", resource_id=user.id)
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código do autenticador inválido")
    record_audit(db, actor=user, action="auth.login", resource_type="session", resource_id=user.id)
    db.commit()
    set_auth_cookies(response, create_access_token(user.id, user.role.value, user.token_version))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, user: CurrentUser, db: DbSession):
    record_audit(db, actor=user, action="auth.logout", resource_type="session", resource_id=user.id)
    db.commit()
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
    user.token_version += 1
    record_audit(db, actor=user, action="auth.password_changed", resource_type="user", resource_id=user.id)
    db.commit()


@router.post("/mfa/setup")
def setup_mfa(payload: CurrentPasswordRequest, user: CsrfUser, db: DbSession):
    """Create a pending secret to be scanned by an authenticator app.

    Requiring the current password prevents someone with an unlocked browser from
    silently enrolling their own device.
    """
    if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual inválida")
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    user.mfa_enabled = False
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Unique Clínica")
    image = qrcode.make(uri)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    record_audit(db, actor=user, action="auth.mfa_setup_started", resource_type="user", resource_id=user.id)
    db.commit()
    return {"qr_code": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")}


@router.post("/mfa/enable", status_code=status.HTTP_204_NO_CONTENT)
def enable_mfa(payload: TotpCodeRequest, user: CsrfUser, db: DbSession):
    if not user.mfa_secret or not payload.totp_code or not pyotp.TOTP(user.mfa_secret).verify(payload.totp_code.replace(" ", ""), valid_window=1):
        raise HTTPException(status_code=400, detail="Código do autenticador inválido")
    user.mfa_enabled = True
    user.token_version += 1
    record_audit(db, actor=user, action="auth.mfa_enabled", resource_type="user", resource_id=user.id)
    db.commit()


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
def disable_mfa(payload: CurrentPasswordRequest, user: CsrfUser, db: DbSession):
    if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual inválida")
    user.mfa_enabled = False
    user.mfa_secret = None
    user.token_version += 1
    record_audit(db, actor=user, action="auth.mfa_disabled", resource_type="user", resource_id=user.id)
    db.commit()
