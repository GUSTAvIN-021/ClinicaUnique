from datetime import UTC, date, datetime, time, timedelta
from fastapi import APIRouter
from sqlalchemy import func, select

from app.dependencies.auth import CurrentUser, DbSession
from app.models.entities import Appointment, AppointmentStatus, Patient, Professional, ProfessionalPatient, Role

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(db: DbSession, user: CurrentUser):
    today = date.today(); week_end = today + timedelta(days=6); month_start = today.replace(day=1)
    scope = [] if user.role == Role.ADMIN else [Appointment.professional_id == user.professional_id]
    count = lambda *where: db.scalar(select(func.count()).select_from(Appointment).where(*scope, *where)) or 0
    patient_count_query = select(func.count()).select_from(Patient)
    if user.role == Role.PROFISSIONAL:
        patient_count_query = patient_count_query.join(ProfessionalPatient).where(ProfessionalPatient.professional_id == user.professional_id)
    monthly_patient_query = select(func.count()).select_from(Patient).where(Patient.created_at >= datetime.combine(month_start, time.min, tzinfo=UTC))
    if user.role == Role.PROFISSIONAL:
        monthly_patient_query = monthly_patient_query.join(ProfessionalPatient).where(ProfessionalPatient.professional_id == user.professional_id)
    return {
        "patients": db.scalar(patient_count_query) or 0,
        "active_professionals": db.scalar(select(func.count()).select_from(Professional).where(Professional.active)) or 0,
        "today_appointments": count(Appointment.appointment_date == today),
        "week_appointments": count(Appointment.appointment_date.between(today, week_end)),
        "missed": count(Appointment.status == AppointmentStatus.FALTOU),
        "completed": count(Appointment.status == AppointmentStatus.REALIZADO),
        "cancelled": count(Appointment.status == AppointmentStatus.CANCELADO),
        "monthly_completed": count(Appointment.appointment_date >= month_start, Appointment.status == AppointmentStatus.REALIZADO),
        "monthly_missed": count(Appointment.appointment_date >= month_start, Appointment.status == AppointmentStatus.FALTOU),
        "monthly_cancelled": count(Appointment.appointment_date >= month_start, Appointment.status == AppointmentStatus.CANCELADO),
        "monthly_new_patients": db.scalar(monthly_patient_query) or 0,
    }
