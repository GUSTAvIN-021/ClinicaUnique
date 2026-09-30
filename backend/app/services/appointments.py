from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.entities import Appointment, AppointmentStatus, ProfessionalAvailability


def assert_valid_slot(db: Session, appointment: Appointment, excluded_id: int | None = None) -> None:
    if appointment.start_time >= appointment.end_time:
        raise HTTPException(status_code=422, detail="O horário final deve ser posterior ao inicial")
    availability = db.scalar(select(ProfessionalAvailability).where(
        ProfessionalAvailability.professional_id == appointment.professional_id,
        ProfessionalAvailability.weekday == appointment.appointment_date.weekday(),
        ProfessionalAvailability.start_time <= appointment.start_time,
        ProfessionalAvailability.end_time >= appointment.end_time,
    ))
    if not availability:
        raise HTTPException(status_code=422, detail="Horário fora da disponibilidade do profissional")
    query = select(Appointment).where(
        Appointment.professional_id == appointment.professional_id,
        Appointment.appointment_date == appointment.appointment_date,
        Appointment.status.notin_([AppointmentStatus.CANCELADO]),
        Appointment.start_time < appointment.end_time,
        Appointment.end_time > appointment.start_time,
    )
    if excluded_id:
        query = query.where(Appointment.id != excluded_id)
    if db.scalar(query):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflito de horário para este profissional")
