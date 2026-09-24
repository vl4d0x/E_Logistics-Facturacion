"""Crea (o actualiza la contraseña de) el usuario admin inicial.

Lee SEED_ADMIN_NOMBRE / SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD del entorno (.env).
No se piden credenciales por chat/CLI: son secretos — configúralas en tu .env local
o como variables del servicio en Railway antes de correr este script.

Uso:
    cd backend && python -m scripts.seed_admin
"""
import sys

from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.db import engine
from app.core.security import hash_password
from app.modules.auth.models import RolUsuario, Usuario


def main() -> None:
    settings = get_settings()

    if not settings.seed_admin_email or not settings.seed_admin_password:
        print(
            "🔴 Faltan SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD en el entorno.\n"
            "   Defínelas en backend/.env (ver .env.example) y vuelve a correr este script.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    with Session(engine) as session:
        existing = session.exec(
            select(Usuario).where(Usuario.email == settings.seed_admin_email)
        ).first()

        if existing:
            existing.password_hash = hash_password(settings.seed_admin_password)
            existing.nombre = settings.seed_admin_nombre
            existing.rol = RolUsuario.admin
            existing.activo = True
            session.add(existing)
            session.commit()
            print(f"✅ Admin actualizado: {existing.email}")
            return

        admin = Usuario(
            nombre=settings.seed_admin_nombre,
            email=settings.seed_admin_email,
            password_hash=hash_password(settings.seed_admin_password),
            rol=RolUsuario.admin,
        )
        session.add(admin)
        session.commit()
        print(f"✅ Admin creado: {admin.email}")


if __name__ == "__main__":
    main()
