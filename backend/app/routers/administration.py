from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.dependencies.auth import CsrfUser, CurrentUser, DbSession
from app.models.entities import Patient, Reminder, Role, SpreadsheetEntry
from app.schemas.common import SpreadsheetEntryIn, SpreadsheetEntryOut
from app.services.access import assert_patient_access

router = APIRouter(tags=["Administração"])


def assert_admin(user: CurrentUser) -> None:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")


@router.get("/spreadsheet", response_model=list[SpreadsheetEntryOut])
def list_spreadsheet(db: DbSession, user: CurrentUser, q: str | None = Query(default=None, max_length=100), category: str | None = None):
    assert_admin(user)
    query = select(SpreadsheetEntry)
    if q:
        query = query.where(SpreadsheetEntry.description.ilike(f"%{q.strip()}%"))
    if category:
        query = query.where(SpreadsheetEntry.category == category)
    return db.scalars(query.order_by(SpreadsheetEntry.entry_date.desc(), SpreadsheetEntry.id.desc())).all()


@router.post("/spreadsheet", response_model=SpreadsheetEntryOut, status_code=status.HTTP_201_CREATED)
def create_spreadsheet_entry(payload: SpreadsheetEntryIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    entry = SpreadsheetEntry(**payload.model_dump(), created_by_id=user.id)
    db.add(entry); db.commit(); db.refresh(entry)
    return entry


@router.patch("/spreadsheet/{entry_id}", response_model=SpreadsheetEntryOut)
def update_spreadsheet_entry(entry_id: int, payload: SpreadsheetEntryIn, db: DbSession, user: CsrfUser):
    assert_admin(user)
    entry = db.get(SpreadsheetEntry, entry_id)
    if not entry: raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    for key, value in payload.model_dump().items(): setattr(entry, key, value)
    db.commit(); db.refresh(entry)
    return entry


class ReminderIn(BaseModel):
    patient_id: int = Field(gt=0)
    scheduled_for: datetime


class ReminderOut(ReminderIn):
    id: int
    status: str
    channel: str

    class Config:
        from_attributes = True


@router.get("/reminders", response_model=list[ReminderOut])
def list_reminders(db: DbSession, user: CurrentUser, patient_id: int | None = None):
    query = select(Reminder)
    if patient_id:
        assert_patient_access(db, user, patient_id)
        query = query.where(Reminder.patient_id == patient_id)
    elif user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Informe um paciente autorizado")
    return db.scalars(query.order_by(Reminder.scheduled_for.desc())).all()


@router.post("/reminders", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderIn, db: DbSession, user: CsrfUser):
    assert_patient_access(db, user, payload.patient_id)
    patient = db.get(Patient, payload.patient_id)
    if not patient: raise HTTPException(status_code=404, detail="Paciente não encontrado")
    if not patient.accepts_reminders:
        raise HTTPException(status_code=422, detail="Paciente não aceita lembretes")
    reminder = Reminder(**payload.model_dump(), status="SIMULADO", channel="SIMULADO")
    db.add(reminder); db.commit(); db.refresh(reminder)
    return reminder
