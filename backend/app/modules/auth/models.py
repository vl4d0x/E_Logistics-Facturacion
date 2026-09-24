"""Tabla `usuario` — ver `02-data-model §3.1`."""
import enum
import uuid

from sqlmodel import Field

from app.core.models import TimestampMixin


class RolUsuario(str, enum.Enum):
    admin = "admin"
    operador = "operador"


class Usuario(TimestampMixin, table=True):
    __tablename__ = "usuario"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nombre: str
    email: str = Field(unique=True, index=True, nullable=False)
    password_hash: str
    rol: RolUsuario = Field(nullable=False)
    # FK a operador.id — la tabla `operador` se crea en Fase 1 (catálogos).
    # Se agrega la constraint de FK en la migración de Fase 1; aquí solo la columna.
    operador_id: uuid.UUID | None = Field(default=None, nullable=True)
    activo: bool = Field(default=True)
