from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, JSON, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(str, Enum):
    ADMIN = "ADMIN"
    PROFISSIONAL = "PROFISSIONAL"


class AppointmentStatus(str, Enum):
    AGENDADO = "AGENDADO"
    CONFIRMADO = "CONFIRMADO"
    REALIZADO = "REALIZADO"
    FALTOU = "FALTOU"
    CANCELADO = "CANCELADO"


class Timestamped(Base):
    __abstract__ = True
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(Timestamped):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SqlEnum(Role), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    professional_id: Mapped[int | None] = mapped_column(ForeignKey("professionals.id", ondelete="SET NULL"), unique=True, nullable=True)


class Patient(Timestamped):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepts_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Professional(Timestamped):
    __tablename__ = "professionals"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    professional_registration: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class ProfessionalCategory(Base):
    __tablename__ = "professional_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("professional_id", "name", name="uq_professional_category"),)


class ProfessionalPatient(Base):
    __tablename__ = "professional_patient"
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="CASCADE"), primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Appointment(Timestamped):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    appointment_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    status: Mapped[AppointmentStatus] = mapped_column(SqlEnum(AppointmentStatus), default=AppointmentStatus.AGENDADO, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    __table_args__ = (Index("ix_appointment_professional_slot", "professional_id", "appointment_date", "start_time", "end_time"),)


class ProfessionalAvailability(Timestamped):
    __tablename__ = "professional_availability"
    id: Mapped[int] = mapped_column(primary_key=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0=segunda, 6=domingo
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class MedicalRecord(Timestamped):
    __tablename__ = "medical_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Anamnesis(Timestamped):
    __tablename__ = "anamnesis"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    professional_id: Mapped[int | None] = mapped_column(ForeignKey("professionals.id"), nullable=True)
    template_key: Mapped[str] = mapped_column(String(100), default="general")
    answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Reminder(Timestamped):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="SIMULADO")
    channel: Mapped[str] = mapped_column(String(30), default="SIMULADO")


class SpreadsheetEntry(Timestamped):
    __tablename__ = "spreadsheet_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    entry_type: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
