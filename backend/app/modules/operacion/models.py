"""Tablas de operación en campo — `02-data-model §3.11-3.13`."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field

from app.core.models import TimestampMixin


class InspeccionSalida(TimestampMixin, table=True):
    __tablename__ = "inspeccion_salida"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    servicio_id: uuid.UUID = Field(foreign_key="servicio.id", nullable=False, unique=True)
    operador_id: uuid.UUID = Field(foreign_key="operador.id", nullable=False)
    unidad_id: uuid.UUID = Field(foreign_key="unidad.id", nullable=False)  # snapshot
    unidad_limpia: bool = Field(nullable=False)
    fumigacion_vigente: bool = Field(nullable=False)
    botiquin: bool = Field(nullable=False)
    casco_chaleco: bool = Field(nullable=False)
    aceite_ok: bool = Field(nullable=False)
    anticongelante_ok: bool = Field(nullable=False)
    neumaticos_ok: bool = Field(nullable=False)
    extintor_ok: bool = Field(nullable=False)
    # `02 §3.11` lo describe como columna generada en Postgres (AND de los 8). SQLite
    # (tests) no soporta generated columns de forma portable vía SQLAlchemy, así que se
    # calcula en el service layer al crear la fila — incluso en Postgres real, el valor
    # nunca cambia después de creada (la inspección no se edita), así que no hay riesgo
    # de que se desincronice.
    todo_ok: bool = Field(nullable=False)
    observaciones: str | None = Field(default=None)
    nivel_combustible: Decimal = Field(nullable=False)
    lectura_medidor: dict = Field(sa_column=Column(JSON, nullable=False))
    odometro_km: int | None = Field(default=None)
    realizada_at: datetime = Field(nullable=False)
    registrada_por: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")
    client_action_id: uuid.UUID = Field(nullable=False, unique=True)


class ReporteCierre(TimestampMixin, table=True):
    __tablename__ = "reporte_cierre"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    servicio_id: uuid.UUID = Field(foreign_key="servicio.id", nullable=False, unique=True)
    operador_id: uuid.UUID = Field(foreign_key="operador.id", nullable=False)
    nivel_combustible: Decimal = Field(nullable=False)
    lectura_medidor: dict = Field(sa_column=Column(JSON, nullable=False))
    odometro_km: int | None = Field(default=None)
    cargo_combustible: bool = Field(nullable=False)
    observaciones: str | None = Field(default=None)
    cerrado_at: datetime = Field(nullable=False)
    client_action_id: uuid.UUID = Field(nullable=False, unique=True)


class CargaCombustible(TimestampMixin, table=True):
    __tablename__ = "carga_combustible"
    __table_args__ = (Index("ix_carga_combustible_unidad_fecha", "unidad_id", "cargada_at"),)

    # Puede venir generado en el teléfono (idempotencia offline) — por eso no usa
    # `default_factory`, el caller siempre lo da explícito.
    id: uuid.UUID = Field(primary_key=True)
    servicio_id: uuid.UUID | None = Field(default=None, foreign_key="servicio.id")
    unidad_id: uuid.UUID = Field(foreign_key="unidad.id", nullable=False)
    operador_id: uuid.UUID | None = Field(default=None, foreign_key="operador.id")
    litros: Decimal = Field(nullable=False)
    precio_litro: Decimal = Field(nullable=False)
    importe: Decimal = Field(nullable=False)
    tipo_combustible: str | None = Field(default=None)
    ticket_key: str | None = Field(default=None)
    cargada_at: datetime = Field(nullable=False)
    registrada_por: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")
