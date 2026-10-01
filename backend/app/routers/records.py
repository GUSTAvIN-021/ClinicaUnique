from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import Anamnesis, AnamnesisTemplate, MedicalRecord, Professional, Role
from app.schemas.common import AnamnesisIn, AnamnesisOut, AnamnesisTemplateIn, AnamnesisTemplateOut, AnamnesisUpdateIn, MedicalRecordIn, MedicalRecordOut, MedicalRecordUpdateIn
from app.services.access import assert_patient_access, assert_professional_scope

router = APIRouter(tags=["Prontuários e anamnese"])


def assert_admin(user: CsrfUser) -> None:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")


def record_out(db: DbSession, record: MedicalRecord) -> dict:
    data = {column.name: getattr(record, column.name) for column in MedicalRecord.__table__.columns}
    professional = db.get(Professional, record.professional_id)
    data["professional_name"] = professional.name if professional else None
    return data


@router.get("/medical-records", response_model=list[MedicalRecordOut])
def list_records(patient_id: int, db: DbSession, user: CurrentUser):
    assert_patient_access(db, user, patient_id)
    query = select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
    if user.role == Role.PROFISSIONAL: query = query.where(MedicalRecord.professional_id == user.professional_id)
    return [record_out(db, record) for record in db.scalars(query.order_by(MedicalRecord.record_date.desc())).all()]


@router.get("/medical-records/{record_id}", response_model=MedicalRecordOut)
def get_record(record_id: int, db: DbSession, user: CurrentUser):
    record = db.get(MedicalRecord, record_id)
    if not record: raise HTTPException(status_code=404, detail="Prontuário não encontrado")
    assert_patient_access(db, user, record.patient_id); assert_professional_scope(user, record.professional_id)
    return record_out(db, record)


@router.post("/medical-records", response_model=MedicalRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(payload: MedicalRecordIn, db: DbSession, user: CsrfUser):
    assert_patient_access(db, user, payload.patient_id); assert_professional_scope(user, payload.professional_id)
    record = MedicalRecord(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(record); db.commit(); db.refresh(record)
    return record_out(db, record)


@router.patch("/medical-records/{record_id}", response_model=MedicalRecordOut)
def update_record(record_id: int, payload: MedicalRecordUpdateIn, db: DbSession, user: CsrfUser):
    record = db.get(MedicalRecord, record_id)
    if not record: raise HTTPException(status_code=404, detail="Prontuário não encontrado")
    assert_patient_access(db, user, record.patient_id)
    assert_professional_scope(user, record.professional_id)
    record.record_date = payload.record_date
    record.category = payload.category
    record.content = payload.content
    record.updated_by_id = user.id
    db.commit(); db.refresh(record)
    return record_out(db, record)


@router.delete("/medical-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: DbSession, user: CsrfUser):
    record = db.get(MedicalRecord, record_id)
    if not record: raise HTTPException(status_code=404, detail="Prontuário não encontrado")
    assert_patient_access(db, user, record.patient_id); assert_professional_scope(user, record.professional_id)
    db.delete(record); db.commit()


@router.get("/anamnesis", response_model=list[AnamnesisOut])
def list_anamnesis(patient_id: int, db: DbSession, user: CurrentUser):
    assert_patient_access(db, user, patient_id)
    query = select(Anamnesis).where(Anamnesis.patient_id == patient_id)
    if user.role == Role.PROFISSIONAL: query = query.where((Anamnesis.professional_id == user.professional_id) | (Anamnesis.professional_id.is_(None)))
    return db.scalars(query.order_by(Anamnesis.created_at.desc())).all()


@router.get("/anamnesis/templates", response_model=list[AnamnesisTemplateOut])
def list_anamnesis_templates(db: DbSession, user: CurrentUser):
    query = select(AnamnesisTemplate)
    if user.role == Role.PROFISSIONAL:
        query = query.where(AnamnesisTemplate.active.is_(True))
    return db.scalars(query.order_by(AnamnesisTemplate.category)).all()


@router.post("/anamnesis/templates", response_model=AnamnesisTemplateOut, status_code=status.HTTP_201_CREATED)
def create_anamnesis_template(payload: AnamnesisTemplateIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    category = payload.category.strip()
    if db.scalar(select(AnamnesisTemplate).where(AnamnesisTemplate.category == category)):
        raise HTTPException(status_code=409, detail="Já existe um template para esta especialidade")
    item = AnamnesisTemplate(**payload.model_dump(), category=category, created_by_id=user.id, updated_by_id=user.id)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/anamnesis/templates/{template_id}", response_model=AnamnesisTemplateOut)
def update_anamnesis_template(template_id: int, payload: AnamnesisTemplateIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    item = db.get(AnamnesisTemplate, template_id)
    if not item: raise HTTPException(status_code=404, detail="Template não encontrado")
    category = payload.category.strip()
    duplicate = db.scalar(select(AnamnesisTemplate).where(AnamnesisTemplate.category == category, AnamnesisTemplate.id != template_id))
    if duplicate: raise HTTPException(status_code=409, detail="Já existe um template para esta especialidade")
    item.category = category; item.fields = [field.model_dump() for field in payload.fields]; item.active = payload.active; item.updated_by_id = user.id
    db.commit(); db.refresh(item)
    return item


@router.delete("/anamnesis/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anamnesis_template(template_id: int, db: DbSession, user: CsrfUser):
    assert_admin(user)
    item = db.get(AnamnesisTemplate, template_id)
    if not item: raise HTTPException(status_code=404, detail="Template não encontrado")
    db.delete(item); db.commit()


@router.post("/anamnesis", response_model=AnamnesisOut, status_code=status.HTTP_201_CREATED)
def create_anamnesis(payload: AnamnesisIn, db: DbSession, user: CsrfUser):
    assert_patient_access(db, user, payload.patient_id)
    if payload.professional_id: assert_professional_scope(user, payload.professional_id)
    elif user.role == Role.PROFISSIONAL: payload.professional_id = user.professional_id
    item = Anamnesis(**payload.model_dump(), created_by_id=user.id)
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.patch("/anamnesis/{anamnesis_id}", response_model=AnamnesisOut)
def update_anamnesis(anamnesis_id: int, payload: AnamnesisUpdateIn, db: DbSession, user: CsrfUser):
    item = db.get(Anamnesis, anamnesis_id)
    if not item: raise HTTPException(status_code=404, detail="Anamnese não encontrada")
    assert_patient_access(db, user, item.patient_id)
    if user.role == Role.PROFISSIONAL and item.professional_id != user.professional_id:
        raise HTTPException(status_code=403, detail="Acesso não autorizado à anamnese")
    item.answers = payload.answers
    db.commit(); db.refresh(item)
    return item


@router.delete("/anamnesis/{anamnesis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anamnesis(anamnesis_id: int, db: DbSession, user: CsrfUser):
    item = db.get(Anamnesis, anamnesis_id)
    if not item: raise HTTPException(status_code=404, detail="Anamnese não encontrada")
    assert_patient_access(db, user, item.patient_id)
    if user.role == Role.PROFISSIONAL and item.professional_id != user.professional_id:
        raise HTTPException(status_code=403, detail="Acesso não autorizado à anamnese")
    db.delete(item); db.commit()
