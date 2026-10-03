"""Tabla `factura` — `02-data-model §3.14`. Solo el modelo por ahora (H4.1-H4.3);
el servicio de timbrado real (H4.7) llega cuando exista el sandbox de Facturama.
"""
import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Column, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field

from app.core.models import TimestampMixin

_ENVIO_DESTINATARIOS_TYPE = JSON().with_variant(ARRAY(String), "postgresql")


class EstadoFactura(str, enum.Enum):
    timbrada = "timbrada"
    cancelacion_pendiente = "cancelacion_pendiente"
    cancelada = "cancelada"
    error = "error"


class EstadoCobro(str, enum.Enum):
    pendiente = "pendiente"
    parcial = "parcial"
    pagada = "pagada"


class Factura(TimestampMixin, table=True):
    __tablename__ = "factura"
    __table_args__ = (
        Index("ix_factura_estado_fecha_emision", "estado", "fecha_emision"),
        Index("ix_factura_estado_cobro", "estado_cobro"),
        # Único parcial: un servicio no puede tener más de una factura "vigente" (`02 §3.14`).
        Index(
            "uq_factura_servicio_vigente",
            "servicio_id",
            unique=True,
            postgresql_where=text("estado IN ('timbrada', 'cancelacion_pendiente')"),
            sqlite_where=text("estado IN ('timbrada', 'cancelacion_pendiente')"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    servicio_id: uuid.UUID = Field(foreign_key="servicio.id", nullable=False, index=True)
    estado: EstadoFactura = Field(nullable=False)
    uuid_fiscal: str | None = Field(default=None, unique=True)
    serie: str | None = Field(default=None)
    folio: str | None = Field(default=None)
    fecha_emision: datetime | None = Field(default=None)
    metodo_pago: str = Field(nullable=False)
    forma_pago: str = Field(default="99", nullable=False)
    uso_cfdi: str = Field(nullable=False)
    # `NUMERIC(12,2)` explícito (`02-data-model §intro`, "Dinero") -- sin esto, el
    # driver redondea a una escala por defecto (ej. "1848.0000000000") al releer.
    subtotal: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    iva_trasladado: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    iva_retenido: Decimal = Field(default=Decimal(0), sa_column=Column(Numeric(12, 2), nullable=False))
    total: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    saldo_insoluto: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    estado_cobro: EstadoCobro = Field(default=EstadoCobro.pendiente, nullable=False)
    payload: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    facturama_id: str | None = Field(default=None)
    xml_key: str | None = Field(default=None)
    pdf_key: str | None = Field(default=None)
    error_detalle: str | None = Field(default=None)
    motivo_cancelacion: str | None = Field(default=None)
    uuid_sustitucion: str | None = Field(default=None)
    cancelacion_solicitada_at: datetime | None = Field(default=None)
    cancelada_at: datetime | None = Field(default=None)
    acuse_cancelacion_key: str | None = Field(default=None)
    estatus_consultado_at: datetime | None = Field(default=None)
    enviado_at: datetime | None = Field(default=None)
    envio_destinatarios: list[str] | None = Field(
        default=None, sa_column=Column(_ENVIO_DESTINATARIOS_TYPE, nullable=True)
    )
    envio_error: str | None = Field(default=None)
    timbrado_at: datetime | None = Field(default=None)
