"""Password hashing and JWT encode/decode."""
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

TokenType = Literal["access", "refresh"]

# bcrypt (la librería, no passlib) directo: passlib 1.7.4 (su último release) es
# incompatible con bcrypt>=4.1 (`AttributeError: module 'bcrypt' has no attribute
# '__about__'`, atrapado en silencio pero ensucia cada login en los logs).
_MAX_PASSWORD_BYTES = 72  # bcrypt trunca en silencio pasado esto; lo hacemos explícito.


def hash_password(plain_password: str) -> str:
    encoded = plain_password.encode("utf-8")
    if len(encoded) > _MAX_PASSWORD_BYTES:
        raise ValueError(f"La contraseña no puede exceder {_MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def _create_token(subject: UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    return _create_token(user_id, "access", timedelta(minutes=settings.jwt_access_minutes))


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.jwt_refresh_days))


class InvalidTokenError(Exception):
    pass


def decode_token(token: str, expected_type: TokenType) -> UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"expected token type '{expected_type}'")

    sub = payload.get("sub")
    if sub is None:
        raise InvalidTokenError("missing subject")

    try:
        return UUID(sub)
    except ValueError as exc:
        raise InvalidTokenError("invalid subject") from exc
