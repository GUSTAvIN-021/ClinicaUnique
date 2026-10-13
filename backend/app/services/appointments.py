from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.entities import Appointment, AppointmentSeries, AppointmentStatus, ProfessionalAvailability


def materialize_recurring_appointments(
    db: Session, date_from: date, date_to: date, professional_id: int | None = None,
) -> bool:
    """Create only the weekly occurrences needed for the requested period."""
    if date_to < date_from:
        return False
    query = select(AppointmentSeries).where(
        AppointmentSeries.active.is_(True),
        AppointmentSeries.starts_on <= date_to,
    )
    if professional_id:
        query = query.where(AppointmentSeries.professional_id == professional_id)
    series_list = db.scalars(query).all()
    if not series_list:
        return False

    series_ids = [series.id for series in series_list]
    existing = {
        (group_id, appointment_date)
        for group_id, appointment_date in db.execute(
            select(Appointment.recurrence_group_id, Appointment.appointment_date).where(
                Appointment.recurrence_group_id.in_(series_ids),
                Appointment.appointment_date >= date_from,
                Appointment.appointment_date <= date_to,
            )
        )
    }
    created = False
    for series in series_list:
        occurrence = series.starts_on
        if occurrence < date_from:
            weeks_to_skip = (date_from - occurrence).days // 7
            occurrence += timedelta(weeks=weeks_to_skip)
            while occurrence < date_from:
                occurrence += timedelta(weeks=1)
        while occurrence <= date_to:
            if (series.id, occurrence) not in existing:
                db.add(Appointment(
                    patient_id=series.patient_id,
                    professional_id=series.professional_id,
                    appointment_date=occurrence,
                    start_time=series.start_time,
                    end_time=series.end_time,
                    service_type=series.service_type,
                    notes=series.notes,
                    recurrence_group_id=series.id,
                    created_by_id=series.created_by_id,
                    updated_by_id=series.updated_by_id,
                ))
                created = True
            occurrence += timedelta(weeks=1)
    return created


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
        Appointment.status.notin_([AppointmentStatus.CANCELADO, AppointmentStatus.FALTOU, AppointmentStatus.FALTOU_PROFISSIONAL]),
        Appointment.start_time < appointment.end_time,
        Appointment.end_time > appointment.start_time,
    )
    if excluded_id:
        query = query.where(Appointment.id != excluded_id)
    if db.scalar(query):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflito de horário para este profissional")
