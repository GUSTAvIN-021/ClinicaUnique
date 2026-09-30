from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.core.security import hash_password
from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import Professional, Role, User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["Usuários"])


class CreateProfessionalUser(BaseModel):
    professional_id: int = Field(gt=0)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class AdminPasswordChange(BaseModel):
    new_password: str = Field(min_length=12, max_length=128)


def admin_only(user: User) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, user: CurrentUser):
    admin_only(user)
    return db.scalars(select(User).order_by(User.email)).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateProfessionalUser, db: DbSession, user: CsrfUser):
    admin_only(user)
    if not db.get(Professional, payload.professional_id): raise HTTPException(status_code=404, detail="Profissional não encontrado")
    if db.scalar(select(User).where(User.email == payload.email.lower())): raise HTTPException(status_code=409, detail="E-mail já está em uso")
    if db.scalar(select(User).where(User.professional_id == payload.professional_id)): raise HTTPException(status_code=409, detail="Profissional já possui acesso")
    item = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=Role.PROFISSIONAL, professional_id=payload.professional_id)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.post("/{user_id}/change-password", status_code=status.HTTP_204_NO_CONTENT)
def admin_change_password(user_id: int, payload: AdminPasswordChange, db: DbSession, user: CsrfUser):
    admin_only(user)
    target = db.get(User, user_id)
    if not target: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    target.password_hash = hash_password(payload.new_password); db.commit()


@router.patch("/{user_id}/active", response_model=UserOut)
def set_active(user_id: int, active: bool, db: DbSession, user: CsrfUser):
    admin_only(user)
    target = db.get(User, user_id)
    if not target: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    target.active = active; db.commit(); db.refresh(target)
    return target
