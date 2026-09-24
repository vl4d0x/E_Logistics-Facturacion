"""DTOs de entrada/salida — ver `03-api-contract §3`."""
import uuid

from pydantic import BaseModel, EmailStr

from app.modules.auth.models import RolUsuario


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    nombre: str
    email: str
    rol: RolUsuario
    operador_id: uuid.UUID | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class RefreshResponse(BaseModel):
    access_token: str
