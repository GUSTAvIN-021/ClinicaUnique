from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, select

from app.dependencies.auth import CurrentUser, CsrfUser, DbSession
from app.models.entities import Category, Patient, Professional, ProfessionalCategory, ProfessionalPatient, Role, User
from app.schemas.common import ProfessionalIn, ProfessionalOut

router = APIRouter(prefix="/professionals", tags=["Profissionais"])


def assert_admin(user: CsrfUser) -> None:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")


def as_out(db: DbSession, professional: Professional) -> dict:
    data = {column.name: getattr(professional, column.name) for column in Professional.__table__.columns}
    data["categories"] = list(db.scalars(select(ProfessionalCategory.name).where(ProfessionalCategory.professional_id == professional.id)))
    return data


def assert_valid_categories(db: DbSession, categories: list[str]) -> list[str]:
    requested = {category.strip() for category in categories if category.strip()}
    available = set(db.scalars(select(Category.name).where(Category.active.is_(True), Category.name.in_(requested))))
    unknown = requested - available
    if unknown:
        raise HTTPException(status_code=422, detail=f"Categoria inválida ou inativa: {', '.join(sorted(unknown))}")
    return sorted(requested)


@router.get("", response_model=list[ProfessionalOut])
def list_professionals(db: DbSession, user: CurrentUser, q: str | None = None, category: str | None = None):
    query = select(Professional)
    if q: query = query.where(Professional.name.ilike(f"%{q.strip()}%"))
    if category: query = query.join(ProfessionalCategory).where(ProfessionalCategory.name.ilike(category))
    if user.role == Role.PROFISSIONAL: query = query.where(Professional.id == user.professional_id)
    return [as_out(db, p) for p in db.scalars(query.order_by(Professional.name)).all()]


@router.post("", response_model=ProfessionalOut, status_code=status.HTTP_201_CREATED)
def create_professional(payload: ProfessionalIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    categories = assert_valid_categories(db, payload.categories)
    data = payload.model_dump(exclude={"categories"})
    professional = Professional(**data)
    db.add(professional); db.flush()
    db.add_all([ProfessionalCategory(professional_id=professional.id, name=name) for name in categories])
    db.commit(); db.refresh(professional)
    return as_out(db, professional)


@router.get("/{professional_id}", response_model=ProfessionalOut)
def get_professional(professional_id: int, db: DbSession, user: CurrentUser):
    if user.role == Role.PROFISSIONAL and user.professional_id != professional_id:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    professional = db.get(Professional, professional_id)
    if not professional: raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return as_out(db, professional)


@router.patch("/{professional_id}", response_model=ProfessionalOut)
def update_professional(professional_id: int, payload: ProfessionalIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    categories = assert_valid_categories(db, payload.categories)
    professional = db.get(Professional, professional_id)
    if not professional: raise HTTPException(status_code=404, detail="Profissional não encontrado")
    for key, value in payload.model_dump(exclude={"categories"}).items(): setattr(professional, key, value)
    db.query(ProfessionalCategory).filter(ProfessionalCategory.professional_id == professional_id).delete()
    db.add_all([ProfessionalCategory(professional_id=professional_id, name=name) for name in categories])
    db.commit(); db.refresh(professional)
    return as_out(db, professional)


@router.put("/{professional_id}/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def link_patient(professional_id: int, patient_id: int, db: DbSession, user: CsrfUser):
    assert_admin(user)
    if not db.get(Professional, professional_id) or not db.get(Patient, patient_id):
        raise HTTPException(status_code=404, detail="Profissional ou paciente não encontrado")
    if not db.get(ProfessionalPatient, {"professional_id": professional_id, "patient_id": patient_id}):
        db.add(ProfessionalPatient(professional_id=professional_id, patient_id=patient_id)); db.commit()


@router.delete("/{professional_id}/patients/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_patient(professional_id: int, patient_id: int, db: DbSession, user: CsrfUser):
    assert_admin(user)
    db.execute(delete(ProfessionalPatient).where(ProfessionalPatient.professional_id == professional_id, ProfessionalPatient.patient_id == patient_id)); db.commit()


@router.delete("/{professional_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_professional(professional_id: int, db: DbSession, user: CsrfUser):
    assert_admin(user)
    professional = db.get(Professional, professional_id)
    if not professional: raise HTTPException(status_code=404, detail="Profissional não encontrado")
    professional.active = False
    linked_user = db.scalar(select(User).where(User.professional_id == professional_id))
    if linked_user: linked_user.active = False
    db.commit()


@router.patch("/{professional_id}/active", response_model=ProfessionalOut)
def set_professional_active(professional_id: int, active: bool, db: DbSession, user: CsrfUser):
    assert_admin(user)
    professional = db.get(Professional, professional_id)
    if not professional: raise HTTPException(status_code=404, detail="Profissional não encontrado")
    professional.active = active
    db.commit(); db.refresh(professional)
    return as_out(db, professional)
