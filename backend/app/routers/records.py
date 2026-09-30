from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import Anamnesis, MedicalRecord, Role
from app.schemas.common import AnamnesisIn, AnamnesisOut, MedicalRecordIn, MedicalRecordOut
from app.services.access import assert_patient_access, assert_professional_scope

router = APIRouter(tags=["Prontuários e anamnese"])


@router.get("/medical-records", response_model=list[MedicalRecordOut])
def list_records(patient_id: int, db: DbSession, user: CurrentUser):
    assert_patient_access(db, user, patient_id)
    query = select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
    if user.role == Role.PROFISSIONAL: query = query.where(MedicalRecord.professional_id == user.professional_id)
    return db.scalars(query.order_by(MedicalRecord.record_date.desc())).all()


@router.get("/medical-records/{record_id}", response_model=MedicalRecordOut)
def get_record(record_id: int, db: DbSession, user: CurrentUser):
    record = db.get(MedicalRecord, record_id)
    if not record: raise HTTPException(status_code=404, detail="Prontuário não encontrado")
    assert_patient_access(db, user, record.patient_id); assert_professional_scope(user, record.professional_id)
    return record


@router.post("/medical-records", response_model=MedicalRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(payload: MedicalRecordIn, db: DbSession, user: CsrfUser):
    assert_patient_access(db, user, payload.patient_id); assert_professional_scope(user, payload.professional_id)
    record = MedicalRecord(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(record); db.commit(); db.refresh(record)
    return record


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


@router.post("/anamnesis", response_model=AnamnesisOut, status_code=status.HTTP_201_CREATED)
def create_anamnesis(payload: AnamnesisIn, db: DbSession, user: CsrfUser):
    assert_patient_access(db, user, payload.patient_id)
    if payload.professional_id: assert_professional_scope(user, payload.professional_id)
    elif user.role == Role.PROFISSIONAL: payload.professional_id = user.professional_id
    item = Anamnesis(**payload.model_dump(), created_by_id=user.id)
    db.add(item); db.commit(); db.refresh(item)
    return item
