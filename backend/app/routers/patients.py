from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import Patient, ProfessionalPatient, Role
from app.schemas.common import PatientIn, PatientOut
from app.services.access import assert_patient_access

router = APIRouter(prefix="/patients", tags=["Pacientes"])


@router.get("", response_model=list[PatientOut])
def list_patients(db: DbSession, user: CurrentUser, q: str | None = Query(default=None, max_length=100), active: bool | None = None):
    query = select(Patient)
    if user.role == Role.PROFISSIONAL:
        query = query.join(ProfessionalPatient, ProfessionalPatient.patient_id == Patient.id).where(ProfessionalPatient.professional_id == user.professional_id)
    if q:
        query = query.where(Patient.name.ilike(f"%{q.strip()}%"))
    if active is not None:
        query = query.where(Patient.active == active)
    return db.scalars(query.order_by(Patient.name)).all()


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientIn, db: DbSession, user: CsrfUser):
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem cadastrar pacientes")
    patient = Patient(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    db.add(patient); db.commit(); db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: DbSession, user: CurrentUser):
    assert_patient_access(db, user, patient_id)
    patient = db.get(Patient, patient_id)
    if not patient: raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, payload: PatientIn, db: DbSession, user: CsrfUser):
    if user.role != Role.ADMIN: raise HTTPException(status_code=403, detail="Apenas administradores podem editar pacientes")
    patient = db.get(Patient, patient_id)
    if not patient: raise HTTPException(status_code=404, detail="Paciente não encontrado")
    for key, value in payload.model_dump().items(): setattr(patient, key, value)
    patient.updated_by_id = user.id; db.commit(); db.refresh(patient)
    return patient


@router.delete("/{patient_id}", response_model=PatientOut)
def deactivate_patient(patient_id: int, db: DbSession, user: CsrfUser):
    if user.role != Role.ADMIN: raise HTTPException(status_code=403, detail="Apenas administradores podem desativar pacientes")
    patient = db.get(Patient, patient_id)
    if not patient: raise HTTPException(status_code=404, detail="Paciente não encontrado")
    patient.active = False; patient.updated_by_id = user.id
    db.commit(); db.refresh(patient)
    return patient
