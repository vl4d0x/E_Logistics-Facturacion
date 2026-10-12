"""Tablas de catálogo — ver `02-data-model §3.2-3.6`."""
import enum
import uuid

from sqlalchemy import JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Column, Field, String

from app.core.models import TimestampMixin

# Postgres real usa `text[]` (02-data-model §3.4); SQLite (tests, `conftest.py`) no
# soporta ARRAY, así que ahí cae a JSON — mismo valor Python (`list[str]`) en ambos.
_EMAILS_COLUMN_TYPE = JSON().with_variant(ARRAY(String), "postgresql")


class RegimenReceptor(str, enum.Enum):
    fisica = "fisica"
    moral = "moral"


class ModoAcuse(str, enum.Enum):
    escaneo = "escaneo"
    referencia = "referencia"
    ninguno = "ninguno"


class MetodoPago(str, enum.Enum):
    PUE = "PUE"
    PPD = "PPD"


class TipoMedidor(str, enum.Enum):
    aguja = "aguja"
    barras = "barras"


class Unidad(TimestampMixin, table=True):
    __tablename__ = "unidad"
    __table_args__ = (
        CheckConstraint(
            "tipo_medidor <> 'barras' OR (num_barras >= 2 AND num_barras <= 20)",
            name="ck_unidad_num_barras",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    apodo: str = Field(unique=True, index=True, nullable=False)
    placa: str = Field(unique=True, index=True, nullable=False)
    anio_modelo: int | None = Field(default=None)
    config_vehicular: str = Field(nullable=False)
    peso_bruto_vehicular: float = Field(nullable=False)  # toneladas, NO kg
    capacidad_carga_kg: float | None = Field(default=None)
    perm_sct: str = Field(nullable=False)
    num_permiso_sct: str = Field(nullable=False)
    aseguradora_resp_civil: str | None = Field(default=None)
    poliza_resp_civil: str | None = Field(default=None)
    tipo_medidor: TipoMedidor = Field(default=TipoMedidor.aguja, nullable=False)
    num_barras: int | None = Field(default=None)
    capacidad_tanque_l: float | None = Field(default=None)
    tipo_combustible: str | None = Field(default=None)
    activo: bool = Field(default=True)


class Operador(TimestampMixin, table=True):
    __tablename__ = "operador"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nombre: str = Field(nullable=False)
    rfc: str = Field(nullable=False)
    num_licencia: str = Field(nullable=False)
    telefono: str | None = Field(default=None)
    activo: bool = Field(default=True)


class Cliente(TimestampMixin, table=True):
    __tablename__ = "cliente"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    razon_social: str = Field(nullable=False)
    nombre_comercial: str = Field(nullable=False)
    rfc: str = Field(nullable=False)
    cp_fiscal: str = Field(nullable=False)
    regimen_fiscal: str = Field(nullable=False)
    regimen_receptor: RegimenReceptor = Field(nullable=False)
    uso_cfdi: str = Field(default="G03", nullable=False)
    metodo_pago_default: MetodoPago = Field(default=MetodoPago.PPD, nullable=False)
    modo_acuse: ModoAcuse = Field(default=ModoAcuse.escaneo, nullable=False)
    emails_facturacion: list[str] = Field(
        default_factory=list, sa_column=Column(_EMAILS_COLUMN_TYPE, nullable=False)
    )
    dias_credito: int = Field(default=30, nullable=False)
    # Caso real: Chemital exige su propio folio de remisión dentro del concepto de
    # la factura; es exclusivo de ese cliente, confirmado por Vlad (04 §2).
    requiere_folio_concepto: bool = Field(default=False, nullable=False)
    # Texto del correo de factura con marcadores ({folio}, {dia}, {mes}, {anio}, {operador},
    # {unidad}, {origen}, {destinos}); None = el texto general (`facturas.PLANTILLA_CORREO_DEFAULT`).
    plantilla_correo: str | None = Field(default=None)
    activo: bool = Field(default=True)


class MercanciaFrecuente(TimestampMixin, table=True):
    __tablename__ = "mercancia_frecuente"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cliente_id: uuid.UUID = Field(foreign_key="cliente.id", nullable=False, index=True)
    nombre_humano: str = Field(nullable=False)
    bienes_transp: str = Field(nullable=False)
    clave_unidad: str = Field(nullable=False)
    unidad_desc: str | None = Field(default=None)
    peso_kg_sugerido: float | None = Field(default=None)
    activo: bool = Field(default=True)


class Lugar(TimestampMixin, table=True):
    __tablename__ = "lugar"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cliente_id: uuid.UUID | None = Field(
        default=None, foreign_key="cliente.id", nullable=True, index=True
    )
    nombre: str = Field(nullable=False)
    rfc_remitente_destinatario: str = Field(default="XAXX010101000", nullable=False)
    nombre_remitente_destinatario: str | None = Field(default=None)
    calle: str | None = Field(default=None)
    num_exterior: str | None = Field(default=None)
    colonia: str | None = Field(default=None)
    localidad: str | None = Field(default=None)
    municipio: str | None = Field(default=None)
    # Claves numéricas del catálogo SAT (`c_Municipio`/`c_Localidad`), resueltas vía
    # Facturama a partir del CP la primera vez que el lugar se usa en una factura, y
    # cacheadas aquí para no volver a llamar al catálogo (`backend/NOTES.md`).
    municipio_clave: str | None = Field(default=None)
    localidad_clave: str | None = Field(default=None)
    estado: str = Field(nullable=False)
    pais: str = Field(default="MEX", nullable=False)
    codigo_postal: str = Field(nullable=False)
    referencia: str | None = Field(default=None)
    es_origen_predeterminado: bool = Field(default=False)
    # Km típico hasta este lugar (importado del Excel de Carta Porte). Solo cuenta como dato
    # del cliente cuando `km_confirmado`; si no, el sugeridor usa 70 km "no confirmado".
    distancia_km: float | None = Field(default=None)
    km_confirmado: bool = Field(default=False, nullable=False)
    activo: bool = Field(default=True)
