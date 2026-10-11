"""Tablas de servicios y viajes — `02-data-model §3.7-3.10`."""
import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.core.models import TimestampMixin


class EstadoServicio(str, enum.Enum):
    programado = "programado"
    en_curso = "en_curso"
    terminado = "terminado"
    cancelado = "cancelado"


class EstadoFacturacion(str, enum.Enum):
    pendiente = "pendiente"
    facturado = "facturado"


class TipoViaje(str, enum.Enum):
    recoleccion = "recoleccion"
    entrega = "entrega"
    recoleccion_entrega = "recoleccion_entrega"


class EstadoViaje(str, enum.Enum):
    pendiente = "pendiente"
    terminado = "terminado"


class TipoAcuse(str, enum.Enum):
    escaneo = "escaneo"
    referencia = "referencia"


class Servicio(TimestampMixin, table=True):
    __tablename__ = "servicio"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # No es un SERIAL de Postgres de verdad: `numero` no es la PK, y SQLite (tests) no
    # soporta autoincrement en columnas que no son PK. Se calcula en el service layer
    # (MAX(numero)+1 en la misma transacción) — a esta escala (decenas de servicios al
    # mes, 1-2 admins) el riesgo de carrera es nulo; no vale la pena una secuencia real.
    numero: int = Field(nullable=False, unique=True, index=True)
    cliente_id: uuid.UUID = Field(foreign_key="cliente.id", nullable=False, index=True)
    unidad_id: uuid.UUID = Field(foreign_key="unidad.id", nullable=False, index=True)
    operador_id: uuid.UUID = Field(foreign_key="operador.id", nullable=False, index=True)
    fecha: date = Field(nullable=False)
    estado: EstadoServicio = Field(default=EstadoServicio.programado, nullable=False)
    estado_facturacion: EstadoFacturacion = Field(
        default=EstadoFacturacion.pendiente, nullable=False
    )
    timbrado_anticipado: bool = Field(default=False, nullable=False)
    # 'precio' = timbrar con el subtotal; 'cero' = timbrar con $0.10, dejar descargar y
    # cancelar solo (cliente que pide la Carta Porte antes de acordar el precio). Vuelve a
    # 'precio' al consumirse, para que el siguiente timbrado use el precio real.
    timbrado_modo: str = Field(default="precio", nullable=False)
    subtotal: Decimal | None = Field(default=None)
    descripcion_concepto: str | None = Field(default=None)
    # Folio propio del cliente (ej. su remisión) para el concepto de la factura --
    # solo lo exigen clientes con `cliente.requiere_folio_concepto` (ej. Chemital).
    folio_cliente: str | None = Field(default=None)
    metodo_pago: str | None = Field(default=None)
    uso_cfdi: str | None = Field(default=None)
    notas: str | None = Field(default=None)
    iniciado_at: datetime | None = Field(default=None)
    terminado_at: datetime | None = Field(default=None)
    terminado_por_admin: bool = Field(default=False, nullable=False)
    cancelado_motivo: str | None = Field(default=None)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")


class Viaje(TimestampMixin, table=True):
    __tablename__ = "viaje"
    __table_args__ = (UniqueConstraint("servicio_id", "orden", name="uq_viaje_servicio_orden"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    servicio_id: uuid.UUID = Field(foreign_key="servicio.id", nullable=False, index=True)
    orden: int = Field(nullable=False)
    tipo: TipoViaje = Field(nullable=False)
    estado: EstadoViaje = Field(default=EstadoViaje.pendiente, nullable=False)
    fecha: date = Field(nullable=False)
    hora_salida_programada: time | None = Field(default=None)
    hora_llegada_programada: time | None = Field(default=None)
    origen_lugar_id: uuid.UUID | None = Field(default=None, foreign_key="lugar.id")
    destino_lugar_id: uuid.UUID | None = Field(default=None, foreign_key="lugar.id")
    distancia_km: float | None = Field(default=None)
    km_reportado: float | None = Field(default=None)
    hora_llegada: time | None = Field(default=None)
    terminado_at: datetime | None = Field(default=None)
    terminado_por: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")
    notas_admin: str | None = Field(default=None)
    notas_operador: str | None = Field(default=None)
    client_action_id: uuid.UUID | None = Field(default=None, unique=True)


class ViajeMercancia(TimestampMixin, table=True):
    __tablename__ = "viaje_mercancia"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    viaje_id: uuid.UUID = Field(foreign_key="viaje.id", nullable=False, index=True)
    mercancia_frecuente_id: uuid.UUID | None = Field(
        default=None, foreign_key="mercancia_frecuente.id"
    )
    descripcion: str = Field(nullable=False)
    bienes_transp: str = Field(nullable=False)
    clave_unidad: str = Field(nullable=False)
    unidad_desc: str | None = Field(default=None)
    cantidad: Decimal = Field(default=Decimal(1), nullable=False)
    peso_kg: float = Field(nullable=False)


class Acuse(TimestampMixin, table=True):
    __tablename__ = "acuse"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    viaje_id: uuid.UUID = Field(foreign_key="viaje.id", nullable=False, index=True)
    tipo: TipoAcuse = Field(nullable=False)
    archivo_key: str | None = Field(default=None)
    mime: str | None = Field(default=None)
    pagina: int = Field(default=1, nullable=False)
    referencia: str | None = Field(default=None)
    subido_por: uuid.UUID | None = Field(default=None, foreign_key="usuario.id")
    subido_at: datetime = Field(nullable=False)
    client_action_id: uuid.UUID | None = Field(default=None, unique=True)
