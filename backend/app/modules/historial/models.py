"""Historial de movimientos de los admins (11 nov 2026).

Solo se registra lo que ocurre desde que existe la tabla: no hay relleno de días anteriores.
`servicio_id`/`factura_id` NO son llaves foráneas a propósito: el historial no debe impedir ni
perderse si algún día se limpia la operación.
"""
import uuid

from sqlalchemy import Index
from sqlmodel import Field

from app.core.models import TimestampMixin

# Tipos de movimiento (columna `tipo`).
FACTURA_TIMBRADA = "factura_timbrada"
FACTURA_ENVIADA = "factura_enviada"
FACTURA_CANCELADA = "factura_cancelada"
SERVICIO_CANCELADO = "servicio_cancelado"

ETIQUETAS = {
    FACTURA_TIMBRADA: "Facturó",
    FACTURA_ENVIADA: "Envió factura",
    FACTURA_CANCELADA: "Canceló factura",
    SERVICIO_CANCELADO: "Canceló servicio",
}


class Movimiento(TimestampMixin, table=True):
    __tablename__ = "movimiento"
    __table_args__ = (Index("ix_movimiento_created_at", "created_at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    usuario_id: uuid.UUID = Field(foreign_key="usuario.id", nullable=False, index=True)
    tipo: str = Field(nullable=False, index=True)
    descripcion: str = Field(nullable=False)
    servicio_id: uuid.UUID | None = Field(default=None)
    factura_id: uuid.UUID | None = Field(default=None)
