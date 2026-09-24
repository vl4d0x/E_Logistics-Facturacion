"""Piezas compartidas por los modelos SQLModel de todos los módulos.

`02-data-model §intro`: todas las tablas llevan `created_at`/`updated_at`
(timestamptz, UTC) y PK `UUID`. Los módulos futuros (catalogos, viajes,
servicios, facturacion...) reusan `TimestampMixin` en vez de repetir esto.
"""
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """`datetime.utcnow()` devuelve naive; SQLAlchemy 2.x exige aware. Usa siempre esto."""
    return datetime.now(UTC)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
