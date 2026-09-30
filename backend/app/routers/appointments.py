from datetime import date
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import Appointment, AppointmentStatus, ProfessionalAvailability, Role
from app.schemas.common import AppointmentIn, AppointmentOut, AppointmentStatusIn, AvailabilityIn, AvailabilityOut
from app.services.access import assert_patient_access, assert_professional_scope
from app.services.appointments import assert_valid_slot

router = APIRouter(tags=["Agenda e disponibilidade"])


@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(db: DbSession, user: CurrentUser, date_from: date | None = None, date_to: date | None = None, professional_id: int | None = None, patient_id: int | None = None, status_filter: AppointmentStatus | None = Query(default=None, alias="status")):
    query = select(Appointment)
    if user.role == Role.PROFISSIONAL:
        query = query.where(Appointment.professional_id == user.professional_id)
    elif professional_id: query = query.where(Appointment.professional_id == professional_id)
    if patient_id:
        assert_patient_access(db, user, patient_id); query = query.where(Appointment.patient_id == patient_id)
    if date_from: query = query.where(Appointment.appointment_date >= date_from)
    if date_to: query = query.where(Appointment.appointment_date <= date_to)
    if status_filter: query = query.where(Appointment.status == status_filter)
    return db.scalars(query.order_by(Appointment.appointment_date, Appointment.start_time)).all()


@router.post("/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentIn, db: DbSession, user: CsrfUser):
    assert_professional_scope(user, payload.professional_id)
    assert_patient_access(db, user, payload.patient_id)
    appointment = Appointment(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    assert_valid_slot(db, appointment)
    db.add(appointment); db.commit(); db.refresh(appointment)
    return appointment


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, payload: AppointmentIn, db: DbSession, user: CsrfUser):
    appointment = db.get(Appointment, appointment_id)
    if not appointment: raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    assert_professional_scope(user, appointment.professional_id)
    assert_patient_access(db, user, appointment.patient_id)
    for key, value in payload.model_dump().items(): setattr(appointment, key, value)
    assert_professional_scope(user, appointment.professional_id); assert_patient_access(db, user, appointment.patient_id)
    assert_valid_slot(db, appointment, appointment_id)
    appointment.updated_by_id = user.id; db.commit(); db.refresh(appointment)
    return appointment


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentOut)
def update_appointment_status(appointment_id: int, payload: AppointmentStatusIn, db: DbSession, user: CsrfUser):
    appointment = db.get(Appointment, appointment_id)
    if not appointment: raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    assert_professional_scope(user, appointment.professional_id)
    assert_patient_access(db, user, appointment.patient_id)
    appointment.status = AppointmentStatus(payload.status)
    appointment.updated_by_id = user.id; db.commit(); db.refresh(appointment)
    return appointment


@router.get("/availability/{professional_id}", response_model=list[AvailabilityOut])
def list_availability(professional_id: int, db: DbSession, user: CurrentUser):
    assert_professional_scope(user, professional_id)
    return db.scalars(select(ProfessionalAvailability).where(ProfessionalAvailability.professional_id == professional_id).order_by(ProfessionalAvailability.weekday, ProfessionalAvailability.start_time)).all()


@router.post("/availability/{professional_id}", response_model=AvailabilityOut, status_code=status.HTTP_201_CREATED)
def add_availability(professional_id: int, payload: AvailabilityIn, db: DbSession, user: CsrfUser):
    if user.role != Role.ADMIN and user.professional_id != professional_id: raise HTTPException(status_code=403, detail="Acesso não autorizado")
    if payload.start_time >= payload.end_time: raise HTTPException(status_code=422, detail="Intervalo de disponibilidade inválido")
    item = ProfessionalAvailability(professional_id=professional_id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item


@router.delete("/availability/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(availability_id: int, db: DbSession, user: CsrfUser):
    item = db.get(ProfessionalAvailability, availability_id)
    if not item: raise HTTPException(status_code=404, detail="Disponibilidade não encontrada")
    if user.role != Role.ADMIN and user.professional_id != item.professional_id:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    db.delete(item); db.commit()
