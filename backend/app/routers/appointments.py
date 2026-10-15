from datetime import date
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import Appointment, AppointmentSeries, AppointmentStatus, ProfessionalAvailability, Role
from app.schemas.common import AppointmentIn, AppointmentOut, AppointmentRecurrenceIn, AppointmentStatusIn, AppointmentUpdateIn, AvailabilityIn, AvailabilityOut
from app.services.access import assert_patient_access, assert_professional_scope
from app.services.appointments import assert_valid_slot, materialize_recurring_appointments

router = APIRouter(tags=["Agenda e disponibilidade"])


@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(db: DbSession, user: CurrentUser, date_from: date | None = None, date_to: date | None = None, professional_id: int | None = None, patient_id: int | None = None, status_filter: AppointmentStatus | None = Query(default=None, alias="status")):
    scoped_professional_id = user.professional_id if user.role == Role.PROFISSIONAL else professional_id
    if date_from and date_to and materialize_recurring_appointments(db, date_from, date_to, scoped_professional_id):
        db.commit()
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
    materialize_recurring_appointments(db, payload.appointment_date, payload.appointment_date, payload.professional_id)
    appointment = Appointment(**payload.model_dump(), created_by_id=user.id, updated_by_id=user.id)
    assert_valid_slot(db, appointment)
    db.add(appointment); db.commit(); db.refresh(appointment)
    return appointment


@router.post("/appointments/recurring", response_model=list[AppointmentOut], status_code=status.HTTP_201_CREATED)
def create_recurring_appointments(payload: AppointmentRecurrenceIn, db: DbSession, user: CsrfUser):
    assert_professional_scope(user, payload.professional_id)
    assert_patient_access(db, user, payload.patient_id)
    recurrence_group_id = str(uuid4())
    materialize_recurring_appointments(db, payload.appointment_date, payload.appointment_date, payload.professional_id)
    base_data = payload.model_dump()
    series = AppointmentSeries(
        id=recurrence_group_id,
        patient_id=payload.patient_id,
        professional_id=payload.professional_id,
        starts_on=payload.appointment_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        service_type=payload.service_type,
        notes=payload.notes,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    appointment = Appointment(
        **base_data,
        recurrence_group_id=recurrence_group_id,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    assert_valid_slot(db, appointment)
    db.add_all([series, appointment])
    db.commit()
    db.refresh(appointment)
    return [appointment]


@router.patch("/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, payload: AppointmentUpdateIn, db: DbSession, user: CsrfUser):
    appointment = db.get(Appointment, appointment_id)
    if not appointment: raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    assert_professional_scope(user, appointment.professional_id)
    assert_patient_access(db, user, appointment.patient_id)
    for key, value in payload.model_dump().items(): setattr(appointment, key, value)
    assert_professional_scope(user, appointment.professional_id); assert_patient_access(db, user, appointment.patient_id)
    materialize_recurring_appointments(db, appointment.appointment_date, appointment.appointment_date, appointment.professional_id)
    assert_valid_slot(db, appointment, appointment_id)
    appointment.updated_by_id = user.id; db.commit(); db.refresh(appointment)
    return appointment


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentOut)
def update_appointment_status(appointment_id: int, payload: AppointmentStatusIn, db: DbSession, user: CsrfUser):
    appointment = db.get(Appointment, appointment_id)
    if not appointment: raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    assert_professional_scope(user, appointment.professional_id)
    assert_patient_access(db, user, appointment.patient_id)
    previous_status = appointment.status
    appointment.status = AppointmentStatus(payload.status)
    if appointment.status not in {AppointmentStatus.CANCELADO, AppointmentStatus.FALTOU, AppointmentStatus.FALTOU_PROFISSIONAL}:
        try:
            assert_valid_slot(db, appointment, appointment_id)
        except HTTPException:
            appointment.status = previous_status
            raise
    appointment.updated_by_id = user.id; db.commit(); db.refresh(appointment)
    return appointment


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cancelled_appointment(appointment_id: int, db: DbSession, user: CsrfUser):
    """Remove a cancelled item that is no longer useful in the agenda."""
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    assert_professional_scope(user, appointment.professional_id)
    assert_patient_access(db, user, appointment.patient_id)
    if appointment.status != AppointmentStatus.CANCELADO:
        raise HTTPException(status_code=422, detail="Cancele o atendimento antes de excluí-lo definitivamente")
    db.delete(appointment)
    db.commit()


@router.delete("/appointments/{appointment_id}/series", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment_series(appointment_id: int, db: DbSession, user: CsrfUser):
    appointment = db.get(Appointment, appointment_id)
    if not appointment: raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if not appointment.recurrence_group_id:
        raise HTTPException(status_code=422, detail="Este agendamento não pertence a uma série recorrente")
    recurrence = db.get(AppointmentSeries, appointment.recurrence_group_id)
    if recurrence:
        assert_professional_scope(user, recurrence.professional_id)
        assert_patient_access(db, user, recurrence.patient_id)
        recurrence.active = False
        recurrence.updated_by_id = user.id
    series = db.scalars(select(Appointment).where(Appointment.recurrence_group_id == appointment.recurrence_group_id)).all()
    for item in series:
        assert_professional_scope(user, item.professional_id)
        assert_patient_access(db, user, item.patient_id)
        if item.appointment_date >= date.today() and item.status != AppointmentStatus.CANCELADO:
            item.status = AppointmentStatus.CANCELADO
            item.updated_by_id = user.id
    db.commit()


@router.get("/availability/{professional_id}", response_model=list[AvailabilityOut])
def list_availability(professional_id: int, db: DbSession, user: CurrentUser):
    assert_professional_scope(user, professional_id)
    return db.scalars(select(ProfessionalAvailability).where(ProfessionalAvailability.professional_id == professional_id).order_by(ProfessionalAvailability.weekday, ProfessionalAvailability.start_time)).all()


@router.post("/availability/{professional_id}", response_model=AvailabilityOut, status_code=status.HTTP_201_CREATED)
def add_availability(professional_id: int, payload: AvailabilityIn, db: DbSession, user: CsrfUser):
    if user.role != Role.ADMIN and user.professional_id != professional_id: raise HTTPException(status_code=403, detail="Acesso não autorizado")
    if payload.start_time >= payload.end_time: raise HTTPException(status_code=422, detail="Intervalo de disponibilidade inválido")
    overlap = db.scalar(select(ProfessionalAvailability).where(
        ProfessionalAvailability.professional_id == professional_id,
        ProfessionalAvailability.weekday == payload.weekday,
        ProfessionalAvailability.start_time < payload.end_time,
        ProfessionalAvailability.end_time > payload.start_time,
    ))
    if overlap:
        raise HTTPException(status_code=409, detail="Este período se sobrepõe a um horário já configurado")
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
