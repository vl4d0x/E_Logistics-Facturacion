"""Tablas de cobranza — `02-data-model §3.15-3.17`: pago, pago_aplicacion, rep."""
import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Column, Index, Numeric, UniqueConstraint, text
from sqlmodel import Field

from app.core.models import TimestampMixin


class EstadoPago(str, enum.Enum):
    registrado = "registrado"
    aplicado = "aplicado"
    rep_emitido = "rep_emitido"


class EstadoRep(str, enum.Enum):
    timbrado = "timbrado"
    cancelacion_pendiente = "cancelacion_pendiente"
    cancelado = "cancelado"
    error = "error"


def _dinero() -> Column:
    return Column(Numeric(12, 2), nullable=False)


class Pago(TimestampMixin, table=True):
    __tablename__ = "pago"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cliente_id: uuid.UUID = Field(foreign_key="cliente.id", nullable=False, index=True)
    fecha_pago: datetime = Field(nullable=False)
    monto: Decimal = Field(sa_column=_dinero())
    forma_pago: str = Field(default="03", nullable=False)
    moneda: str = Field(default="MXN", nullable=False)
    num_operacion: str | None = Field(default=None)
    rfc_emisor_cta_ord: str | None = Field(default=None)
    cta_ordenante: str | None = Field(default=None)
    rfc_emisor_cta_ben: str | None = Field(default=None)
    cta_beneficiario: str | None = Field(default=None)
    comprobante_key: str | None = Field(default=None)
    notas: str | None = Field(default=None)
    estado: EstadoPago = Field(default=EstadoPago.registrado, nullable=False)
    aplicado_at: datetime | None = Field(default=None)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")


class PagoAplicacion(TimestampMixin, table=True):
    __tablename__ = "pago_aplicacion"
    __table_args__ = (UniqueConstraint("pago_id", "factura_id", name="uq_pago_aplicacion_pago_factura"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pago_id: uuid.UUID = Field(foreign_key="pago.id", nullable=False, index=True)
    factura_id: uuid.UUID = Field(foreign_key="factura.id", nullable=False, index=True)
    monto: Decimal = Field(sa_column=_dinero())
    num_parcialidad: int = Field(nullable=False)
    saldo_anterior: Decimal = Field(sa_column=_dinero())
    saldo_insoluto: Decimal = Field(sa_column=_dinero())
    # Impuestos de esta parcialidad (`06 §5`): las siguientes los leen para que todas sumen
    # exactamente los de la factura.
    base: Decimal = Field(sa_column=_dinero())
    traslado: Decimal = Field(sa_column=_dinero())
    retencion: Decimal = Field(sa_column=_dinero())


class Rep(TimestampMixin, table=True):
    __tablename__ = "rep"
    __table_args__ = (
        Index(
            "uq_rep_pago_vigente",
            "pago_id",
            unique=True,
            postgresql_where=text("estado IN ('timbrado', 'cancelacion_pendiente')"),
            sqlite_where=text("estado IN ('timbrado', 'cancelacion_pendiente')"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    pago_id: uuid.UUID = Field(foreign_key="pago.id", nullable=False, index=True)
    estado: EstadoRep = Field(nullable=False)
    uuid_fiscal: str | None = Field(default=None, unique=True)
    serie: str | None = Field(default=None)
    folio: str | None = Field(default=None)
    fecha_emision: datetime | None = Field(default=None)
    payload: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    facturama_id: str | None = Field(default=None)
    xml_key: str | None = Field(default=None)
    pdf_key: str | None = Field(default=None)
    error_detalle: str | None = Field(default=None)
    motivo_cancelacion: str | None = Field(default=None)
    uuid_sustitucion: str | None = Field(default=None)
    cancelacion_solicitada_at: datetime | None = Field(default=None)
    cancelado_at: datetime | None = Field(default=None)
    acuse_cancelacion_key: str | None = Field(default=None)
    estatus_consultado_at: datetime | None = Field(default=None)
    enviado_at: datetime | None = Field(default=None)
    timbrado_at: datetime | None = Field(default=None)
