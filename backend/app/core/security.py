"""Password hashing and JWT encode/decode."""
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


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
