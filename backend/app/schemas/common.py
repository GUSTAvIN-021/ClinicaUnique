from datetime import date, datetime, time
from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatientIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    birth_date: date | None = None
    cpf: str | None = Field(default=None, max_length=14)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = None
    address: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    notes: str | None = None
    accepts_reminders: bool = True
    active: bool = True


class PatientOut(PatientIn, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class ProfessionalIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: str
    phone: str | None = None
    categories: list[str] = Field(default_factory=list)
    active: bool = True


class ProfessionalOut(ProfessionalIn, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class AppointmentIn(BaseModel):
    patient_id: int = Field(gt=0)
    professional_id: int = Field(gt=0)
    appointment_date: date
    start_time: time
    end_time: time
    status: str = "AGENDADO"
    notes: str | None = None


class AppointmentOut(AppointmentIn, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class AppointmentStatusIn(BaseModel):
    status: str = Field(pattern="^(AGENDADO|CONFIRMADO|REALIZADO|FALTOU|CANCELADO)$")


class AvailabilityIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class AvailabilityOut(AvailabilityIn, ORMModel):
    id: int


class MedicalRecordIn(BaseModel):
    patient_id: int = Field(gt=0)
    professional_id: int = Field(gt=0)
    record_date: date
    category: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class MedicalRecordOut(MedicalRecordIn, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class AnamnesisIn(BaseModel):
    patient_id: int = Field(gt=0)
    professional_id: int | None = Field(default=None, gt=0)
    template_key: str = "general"
    answers: dict = Field(default_factory=dict)


class AnamnesisOut(AnamnesisIn, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class SpreadsheetEntryIn(BaseModel):
    entry_date: date
    description: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    amount_cents: int
    entry_type: str = Field(pattern="^(RECEITA|DESPESA)$")
    notes: str | None = None


class SpreadsheetEntryOut(SpreadsheetEntryIn, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime
