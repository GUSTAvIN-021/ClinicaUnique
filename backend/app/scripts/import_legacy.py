"""Import data exported from the former Emergent/MongoDB application.

Run a simulation first:
    python -m app.scripts.import_legacy --input-dir /imports --dry-run

Apply only after reviewing the report:
    python -m app.scripts.import_legacy --input-dir /imports --apply
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.entities import (
    AnamnesisTemplate, Appointment, AppointmentStatus, Category, LegacyImportMapping,
    MedicalRecord, Patient, Professional, ProfessionalCategory, ProfessionalPatient, Role, User,
)

SOURCE = "emergent"
REQUIRED_FILES = ("patients", "professionals", "categories", "appointments", "anamneses")


class Report:
    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.warnings: list[str] = []

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def show(self) -> None:
        print("\n=== Relatório de migração Emergent → Unique ===")
        for key, value in sorted(self.counts.items()):
            print(f"{key}: {value}")
        if self.warnings:
            print("\nAvisos (primeiros 20):")
            for warning in self.warnings[:20]:
                print(f"- {warning}")
            if len(self.warnings) > 20:
                print(f"- ... e mais {len(self.warnings) - 20} aviso(s)")


def load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError(f"{path.name} deve conter uma lista JSON")
    return [item for item in data if isinstance(item, dict)]


def load_export(directory: Path) -> dict[str, list[dict[str, Any]]]:
    exported: dict[str, list[dict[str, Any]]] = {}
    for name in REQUIRED_FILES:
        path = directory / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Arquivo obrigatório não encontrado: {path}")
        exported[name] = load_json(path)
    records: dict[str, dict[str, Any]] = {}
    for filename in ("prontuarios (1).json", "prontuarios (2).json", "prontuarios.json"):
        path = directory / filename
        if path.exists():
            for record in load_json(path):
                legacy_id = str(record.get("id", "")).strip()
                if legacy_id:
                    records[legacy_id] = record
    if not records:
        raise FileNotFoundError("Inclua ao menos um export de prontuários JSON no diretório de importação")
    exported["records"] = list(records.values())
    return exported


def parse_legacy_date(value: Any) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:26], pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_legacy_time(value: Any) -> time | None:
    if value is None:
        return None
    text = str(value).strip()
    for pattern in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).time()
        except ValueError:
            continue
    return None


def mapping(db, entity_type: str, legacy_id: str) -> LegacyImportMapping | None:
    return db.scalar(select(LegacyImportMapping).where(
        LegacyImportMapping.source == SOURCE,
        LegacyImportMapping.entity_type == entity_type,
        LegacyImportMapping.legacy_id == legacy_id,
    ))


def save_mapping(db, entity_type: str, legacy_id: str, target_id: int, details: dict[str, Any] | None = None) -> None:
    if mapping(db, entity_type, legacy_id):
        return
    db.add(LegacyImportMapping(
        source=SOURCE, entity_type=entity_type, legacy_id=legacy_id, target_id=target_id, details=details or {},
    ))


def admin_user_id(db) -> int:
    user = db.scalar(select(User).where(User.role == Role.ADMIN).order_by(User.id))
    if not user:
        raise RuntimeError("Crie o administrador do Unique antes de importar dados")
    return user.id


def legacy_email(legacy_id: str) -> str:
    return f"legacy-{legacy_id}@imported.invalid".lower()


def category_for_name(db, name: str, actor_id: int) -> Category:
    cleaned = name.strip()
    category = db.scalar(select(Category).where(func.lower(Category.name) == cleaned.lower()))
    if category:
        return category
    category = Category(name=cleaned, active=True, created_by_id=actor_id, updated_by_id=actor_id)
    db.add(category); db.flush()
    return category


def legacy_types(row: dict[str, Any]) -> list[str]:
    values = row.get("tipos") or []
    if isinstance(values, str):
        values = [item.strip() for item in values.split(",")]
    if not values and row.get("tipo"):
        values = [item.strip() for item in str(row["tipo"]).split(",")]
    return sorted({str(item).strip() for item in values if str(item).strip()})


def professional_for_row(db, row: dict[str, Any], actor_id: int, report: Report, orphan: bool = False) -> Professional:
    legacy_id = str(row["id"])
    previous = mapping(db, "professional", legacy_id)
    if previous:
        return db.get(Professional, previous.target_id)
    name = str(row.get("nome") or row.get("profissional_nome") or f"Profissional legado {legacy_id[:8]}").strip()
    if not orphan:
        matches = db.scalars(select(Professional).where(func.lower(Professional.name) == name.lower())).all()
        if len(matches) == 1:
            professional = matches[0]
        else:
            professional = Professional(name=name, email=legacy_email(legacy_id), active=str(row.get("status", "ativo")).lower() != "inativo")
            db.add(professional); db.flush()
    else:
        professional = Professional(name=f"{name} (legado)", email=legacy_email(legacy_id), active=False)
        db.add(professional); db.flush()
        report.counts["profissionais_legados_inativos"] += 1
    for category_name in legacy_types(row):
        category_for_name(db, category_name, actor_id)
        # ProfessionalCategory has its own primary key.  The pair
        # (professional_id, name) is a business/unique key, so it must be
        # queried explicitly instead of passed to Session.get().
        exists = db.scalar(
            select(ProfessionalCategory).where(
                ProfessionalCategory.professional_id == professional.id,
                ProfessionalCategory.name == category_name,
            )
        )
        if not exists:
            db.add(ProfessionalCategory(professional_id=professional.id, name=category_name))
    save_mapping(db, "professional", legacy_id, professional.id)
    report.counts["profissionais_importados_ou_mapeados"] += 1
    return professional


def patient_for_row(db, row: dict[str, Any], actor_id: int, report: Report) -> Patient:
    legacy_id = str(row["id"])
    previous = mapping(db, "patient", legacy_id)
    if previous:
        return db.get(Patient, previous.target_id)
    name = str(row.get("nome") or "Paciente sem nome").strip()
    birth_date = parse_legacy_date(row.get("data_nascimento"))
    # Only reuse a manually created patient when there is a second stable
    # identifier. A name alone is not sufficient for clinical data matching.
    if birth_date:
        matches = db.scalars(select(Patient).where(func.lower(Patient.name) == name.lower(), Patient.birth_date == birth_date)).all()
    elif row.get("telefone"):
        matches = db.scalars(select(Patient).where(func.lower(Patient.name) == name.lower(), Patient.phone == row.get("telefone"))).all()
    else:
        matches = []
    if len(matches) == 1:
        patient = matches[0]
    else:
        legacy_details = {key: row.get(key) for key in ("idade", "endereco", "plano_saude", "numero_carteirinha", "data_primeiro_atendimento", "responsaveis") if row.get(key) not in (None, "", [], {})}
        notes = f"Dados importados do sistema anterior:\n{json.dumps(legacy_details, ensure_ascii=False, indent=2)}" if legacy_details else None
        patient = Patient(
            name=name, birth_date=birth_date, phone=row.get("telefone") or None,
            accepts_reminders=bool(row.get("aceita_lembretes", True)), notes=notes,
            created_by_id=actor_id, updated_by_id=actor_id,
        )
        db.add(patient); db.flush()
    save_mapping(db, "patient", legacy_id, patient.id)
    report.counts["pacientes_importados_ou_mapeados"] += 1
    return patient


def link_patient_professional(db, patient_id: int, professional_id: int) -> None:
    if not db.get(ProfessionalPatient, {"patient_id": patient_id, "professional_id": professional_id}):
        db.add(ProfessionalPatient(patient_id=patient_id, professional_id=professional_id))


def target_id(db, entity_type: str, legacy_id: Any) -> int | None:
    if legacy_id is None:
        return None
    item = mapping(db, entity_type, str(legacy_id))
    return item.target_id if item else None


def appointment_status(value: Any) -> AppointmentStatus:
    statuses = {
        "agendado": AppointmentStatus.AGENDADO, "confirmado": AppointmentStatus.CONFIRMADO,
        "presente": AppointmentStatus.REALIZADO, "realizado": AppointmentStatus.REALIZADO,
        "faltou_paciente": AppointmentStatus.FALTOU, "faltou_profissional": AppointmentStatus.FALTOU,
        "faltou": AppointmentStatus.FALTOU, "cancelado": AppointmentStatus.CANCELADO,
    }
    return statuses.get(str(value or "").lower(), AppointmentStatus.AGENDADO)


def import_templates(db, rows: list[dict[str, Any]], actor_id: int, report: Report) -> None:
    for row in rows:
        legacy_id = str(row.get("id", "")).strip()
        category_name = str(row.get("especialidade", "")).strip()
        if not legacy_id or not category_name:
            report.warn("Template de anamnese sem id ou especialidade foi ignorado")
            continue
        category_for_name(db, category_name, actor_id)
        existing = db.scalar(select(AnamnesisTemplate).where(AnamnesisTemplate.category == category_name))
        if not existing:
            existing = AnamnesisTemplate(
                category=category_name,
                fields=[{"key": "respostas", "label": "Respostas", "field_type": "textarea", "required": False}],
                instructions=str(row.get("conteudo") or ""), active=True, created_by_id=actor_id, updated_by_id=actor_id,
            )
            db.add(existing); db.flush()
        save_mapping(db, "anamnesis_template", legacy_id, existing.id)
        report.counts["templates_anamnese_importados_ou_mapeados"] += 1


def import_all(exported: dict[str, list[dict[str, Any]]], apply: bool) -> Report:
    report = Report()
    report.counts.update({f"origem_{name}": len(rows) for name, rows in exported.items()})
    legacy_patient_ids = {str(row.get("id")) for row in exported["patients"]}
    legacy_professional_ids = {str(row.get("id")) for row in exported["professionals"]}
    for entity, rows in (("agendamentos", exported["appointments"]), ("prontuarios", exported["records"])):
        report.counts[f"{entity}_pacientes_sem_origem"] = sum(str(row.get("paciente_id")) not in legacy_patient_ids for row in rows)
        report.counts[f"{entity}_profissionais_legados"] = sum(str(row.get("profissional_id")) not in legacy_professional_ids for row in rows)
    if not apply:
        report.counts["modo_simulacao"] = 1
        return report
    with SessionLocal() as db:
        try:
            actor_id = admin_user_id(db)
            for row in exported["categories"]:
                name = str(row.get("nome", "")).strip()
                legacy_id = str(row.get("id", "")).strip()
                if name:
                    category = category_for_name(db, name, actor_id)
                    if legacy_id: save_mapping(db, "category", legacy_id, category.id)
                    report.counts["categorias_importadas_ou_mapeadas"] += 1
            for row in exported["professionals"]:
                if row.get("id"): professional_for_row(db, row, actor_id, report)
            for row in exported["patients"]:
                if row.get("id"): patient_for_row(db, row, actor_id, report)
            for row in exported["patients"]:
                patient_id = target_id(db, "patient", row.get("id")); professional_id = target_id(db, "professional", row.get("responsavel_profissional_id"))
                if patient_id and professional_id: link_patient_professional(db, patient_id, professional_id)
            import_templates(db, exported["anamneses"], actor_id, report)
            for row in exported["appointments"]:
                legacy_id = str(row.get("id", "")).strip()
                if not legacy_id or mapping(db, "appointment", legacy_id): continue
                patient_id = target_id(db, "patient", row.get("paciente_id")); professional_id = target_id(db, "professional", row.get("profissional_id"))
                if not professional_id:
                    professional_id = professional_for_row(db, {"id": row.get("profissional_id"), "profissional_nome": row.get("profissional_nome")}, actor_id, report, orphan=True).id
                appointment_date = parse_legacy_date(row.get("data")); start_time = parse_legacy_time(row.get("horario"))
                if not patient_id or not appointment_date or not start_time:
                    report.warn(f"Agendamento {legacy_id} ignorado por dados incompletos"); continue
                duration = int(row.get("duracao") or 30); end_time = (datetime.combine(date.today(), start_time) + timedelta(minutes=duration)).time()
                item = Appointment(patient_id=patient_id, professional_id=professional_id, appointment_date=appointment_date, start_time=start_time, end_time=end_time, status=appointment_status(row.get("status")), notes=row.get("observacoes") or None, recurrence_group_id=str(row.get("grupo_recorrencia") or "")[:36] or None, created_by_id=actor_id, updated_by_id=actor_id)
                db.add(item); db.flush(); save_mapping(db, "appointment", legacy_id, item.id); link_patient_professional(db, patient_id, professional_id); report.counts["agendamentos_importados"] += 1
            for row in exported["records"]:
                legacy_id = str(row.get("id", "")).strip()
                if not legacy_id or mapping(db, "medical_record", legacy_id): continue
                patient_id = target_id(db, "patient", row.get("paciente_id")); professional_id = target_id(db, "professional", row.get("profissional_id"))
                if not professional_id:
                    professional_id = professional_for_row(db, {"id": row.get("profissional_id"), "profissional_nome": row.get("profissional_nome")}, actor_id, report, orphan=True).id
                record_date = parse_legacy_date(row.get("data"))
                if not patient_id or not professional_id or not record_date or not str(row.get("texto", "")).strip():
                    report.warn(f"Prontuário {legacy_id} ignorado por dados incompletos"); continue
                item = MedicalRecord(patient_id=patient_id, professional_id=professional_id, record_date=record_date, category="Prontuário legado", content=str(row["texto"]), created_by_id=actor_id, updated_by_id=actor_id)
                db.add(item); db.flush(); save_mapping(db, "medical_record", legacy_id, item.id, {"legacy_attachments": row.get("anexos") or []}); link_patient_professional(db, patient_id, professional_id); report.counts["prontuarios_importados"] += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa export JSON do sistema Emergent")
    parser.add_argument("--input-dir", type=Path, default=Path("/imports"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Valida os arquivos sem escrever no banco")
    mode.add_argument("--apply", action="store_true", help="Importa os dados; use somente após o dry-run")
    args = parser.parse_args()
    report = import_all(load_export(args.input_dir), apply=args.apply)
    report.show()
    if args.dry_run:
        print("\nSimulação concluída: nenhum dado foi gravado.")
    else:
        print("\nImportação concluída. Execute novamente com --dry-run para conferir os arquivos de origem.")


if __name__ == "__main__":
    main()
