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
    # FK + unique agregadas en Fase 1 (`02-data-model §3.1`, H1.2): un operador tiene
    # a lo más un acceso a la app.
    operador_id: uuid.UUID | None = Field(
        default=None, foreign_key="operador.id", nullable=True, unique=True
    )
    activo: bool = Field(default=True)
