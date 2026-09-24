"""Dependencias de FastAPI: usuario autenticado y protección por rol."""
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.db import get_session
from app.core.errors import AppError
from app.core.security import InvalidTokenError, decode_token
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.auth.service import get_user_by_id

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: Session = Depends(get_session),
) -> Usuario:
    if credentials is None:
        raise AppError("unauthorized", "No autenticado", 401)

    try:
        user_id = decode_token(credentials.credentials, expected_type="access")
    except InvalidTokenError as exc:
        raise AppError("unauthorized", "Token inválido o expirado", 401) from exc

    user = get_user_by_id(session, user_id)
    if user is None or not user.activo:
        raise AppError("unauthorized", "Token inválido o expirado", 401)

    return user


def require_role(*roles: RolUsuario) -> Callable[[Usuario], Usuario]:
    def _dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.rol not in roles:
            raise AppError("forbidden", "No tienes permiso para esta acción", 403)
        return user

    return _dependency
