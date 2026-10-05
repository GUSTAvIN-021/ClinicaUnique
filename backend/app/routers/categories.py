from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import AnamnesisTemplate, Category, ProfessionalCategory, Role
from app.schemas.common import CategoryIn, CategoryOut

router = APIRouter(prefix="/categories", tags=["Categorias"])


def assert_admin(user: CsrfUser) -> None:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")


def normalized_name(name: str) -> str:
    return name.strip()


@router.get("", response_model=list[CategoryOut])
def list_categories(db: DbSession, user: CurrentUser, include_inactive: bool = False):
    query = select(Category)
    if user.role != Role.ADMIN or not include_inactive:
        query = query.where(Category.active.is_(True))
    return db.scalars(query.order_by(Category.name)).all()


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    name = normalized_name(payload.name)
    duplicate = db.scalar(select(Category).where(func.lower(Category.name) == name.lower()))
    if duplicate:
        raise HTTPException(status_code=409, detail="Esta categoria já existe")
    item = Category(name=name, active=payload.active, created_by_id=user.id, updated_by_id=user.id)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    item = db.get(Category, category_id)
    if not item: raise HTTPException(status_code=404, detail="Categoria não encontrada")
    name = normalized_name(payload.name)
    duplicate = db.scalar(select(Category).where(func.lower(Category.name) == name.lower(), Category.id != category_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Esta categoria já existe")
    previous_name = item.name
    item.name = name; item.active = payload.active; item.updated_by_id = user.id
    if previous_name != name:
        for professional_category in db.scalars(select(ProfessionalCategory).where(ProfessionalCategory.name == previous_name)):
            professional_category.name = name
        for template in db.scalars(select(AnamnesisTemplate).where(AnamnesisTemplate.category == previous_name)):
            template.category = name
    db.commit(); db.refresh(item)
    return item


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession, user: CsrfUser):
    assert_admin(user)
    item = db.get(Category, category_id)
    if not item: raise HTTPException(status_code=404, detail="Categoria não encontrada")
    in_professionals = db.scalar(select(ProfessionalCategory.id).where(ProfessionalCategory.name == item.name).limit(1))
    in_templates = db.scalar(select(AnamnesisTemplate.id).where(AnamnesisTemplate.category == item.name).limit(1))
    if in_professionals or in_templates:
        raise HTTPException(status_code=409, detail="Esta categoria está em uso. Desative-a para preservar o histórico.")
    db.delete(item); db.commit()
