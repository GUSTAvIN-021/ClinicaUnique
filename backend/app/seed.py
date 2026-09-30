"""Development-only seed. Requires SEED_ADMIN_PASSWORD explicitly set in .env."""
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Role, User


def main() -> None:
    settings = get_settings()
    if not settings.seed_admin_password:
        raise SystemExit("Defina SEED_ADMIN_PASSWORD no .env antes de criar o administrador.")
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == settings.seed_admin_email.lower()))
        if existing:
            print("Administrador já existe."); return
        db.add(User(email=settings.seed_admin_email.lower(), password_hash=hash_password(settings.seed_admin_password), role=Role.ADMIN))
        db.commit(); print("Administrador de desenvolvimento criado.")


if __name__ == "__main__": main()
