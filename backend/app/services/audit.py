"""Registro de eventos de segurança, sem conteúdo clínico ou senhas."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AuditLog, User


def record_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: str | int,
    details: dict[str, Any] | None = None,
) -> None:
    """Queue a minimal, non-clinical audit event in the current transaction."""
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            details=details or {},
        )
    )
