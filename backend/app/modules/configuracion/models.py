"""Parámetros editables desde la UI — `02-data-model §3.19`."""
import uuid

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.core.models import TimestampMixin


class Configuracion(TimestampMixin, table=True):
    __tablename__ = "configuracion"

    clave: str = Field(primary_key=True)
    valor: dict | list | str | float | bool | None = Field(sa_column=Column(JSON, nullable=False))
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")
