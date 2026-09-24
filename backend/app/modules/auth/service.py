"""Lógica de negocio de auth. Funciones puras que reciben `session`."""
from uuid import UUID

from sqlmodel import Session, select

from app.core.errors import AppError
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import LoginResponse, RefreshResponse, UserOut


def get_user_by_email(session: Session, email: str) -> Usuario | None:
    return session.exec(select(Usuario).where(Usuario.email == email)).first()


def get_user_by_id(session: Session, user_id: UUID) -> Usuario | None:
    return session.get(Usuario, user_id)


def login(session: Session, email: str, password: str) -> LoginResponse:
    user = get_user_by_email(session, email)
    if user is None or not user.activo or not verify_password(password, user.password_hash):
        raise AppError("unauthorized", "Credenciales inválidas", 401)

    return LoginResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=UserOut(
            id=user.id,
            nombre=user.nombre,
            email=user.email,
            rol=user.rol,
            operador_id=user.operador_id,
        ),
    )


def refresh(session: Session, refresh_token: str) -> RefreshResponse:
    try:
        user_id = decode_token(refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise AppError("unauthorized", "Refresh token inválido o expirado", 401) from exc

    user = get_user_by_id(session, user_id)
    if user is None or not user.activo:
        raise AppError("unauthorized", "Refresh token inválido o expirado", 401)

    return RefreshResponse(access_token=create_access_token(user.id))
