from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ProfessionalPatient, Role, User


def assert_patient_access(db: Session, user: User, patient_id: int) -> None:
    if user.role == Role.ADMIN:
        return
    if not user.professional_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil profissional inválido")
    linked = db.scalar(select(ProfessionalPatient).where(
        ProfessionalPatient.professional_id == user.professional_id,
        ProfessionalPatient.patient_id == patient_id,
    ))
    if not linked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não autorizado ao paciente")


def assert_professional_scope(user: User, professional_id: int) -> None:
    if user.role == Role.PROFISSIONAL and user.professional_id != professional_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso não autorizado ao profissional")
