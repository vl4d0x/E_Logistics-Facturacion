"""DTOs de entrada/salida — `03-api-contract §6`."""
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.modules.servicios.models import EstadoFacturacion, EstadoServicio, EstadoViaje, TipoViaje


# --- Viaje / mercancías ------------------------------------------------------
class ViajeMercanciaIn(BaseModel):
    mercancia_frecuente_id: uuid.UUID
    cantidad: Decimal = Decimal(1)
    peso_kg: float


class ViajeMercanciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mercancia_frecuente_id: uuid.UUID | None
    descripcion: str
    bienes_transp: str
    clave_unidad: str
    unidad_desc: str | None
    cantidad: Decimal
    peso_kg: float


class ViajeCreate(BaseModel):
    tipo: TipoViaje
    fecha: date | None = None
    origen_lugar_id: uuid.UUID | None = None
    destino_lugar_id: uuid.UUID | None = None
    distancia_km: float | None = None
    notas_admin: str | None = None
    hora_salida_programada: time | None = None
    hora_llegada_programada: time | None = None
    mercancias: list[ViajeMercanciaIn] | None = None

    @model_validator(mode="after")
    def _check_origen_destino(self) -> "ViajeCreate":
        if self.tipo == TipoViaje.recoleccion and self.origen_lugar_id is None:
            raise ValueError("Una recolección necesita origen_lugar_id")
        if self.tipo == TipoViaje.entrega and self.destino_lugar_id is None:
            raise ValueError("Una entrega necesita destino_lugar_id")
        if self.tipo == TipoViaje.recoleccion_entrega and (
            self.origen_lugar_id is None or self.destino_lugar_id is None
        ):
            raise ValueError("Recolección y entrega necesita origen_lugar_id y destino_lugar_id")
        return self


class ViajeUpdate(BaseModel):
    tipo: TipoViaje | None = None
    fecha: date | None = None
    origen_lugar_id: uuid.UUID | None = None
    destino_lugar_id: uuid.UUID | None = None
    distancia_km: float | None = None
    notas_admin: str | None = None
    hora_salida_programada: time | None = None
    hora_llegada_programada: time | None = None


class LugarResumen(BaseModel):
    id: uuid.UUID
    nombre: str
    codigo_postal: str
    # Dirección completa (opcional): solo se llena para `GET /operador/servicios`
    # (`03 §7`: "lugares completos (nombre, dirección, referencia)") — el admin no la
    # necesita en el resumen, pero no estorba tenerla disponible.
    calle: str | None = None
    num_exterior: str | None = None
    colonia: str | None = None
    municipio: str | None = None
    estado: str | None = None
    referencia: str | None = None
    rfc_remitente_destinatario: str | None = None
    nombre_remitente_destinatario: str | None = None


class AcuseOut(BaseModel):
    id: uuid.UUID
    tipo: str
    url: str | None  # URL firmada de corta duración (`03-api-contract §1`); nunca la key cruda
    mime: str | None
    pagina: int
    referencia: str | None
    subido_at: datetime


class ViajeOut(BaseModel):
    id: uuid.UUID
    orden: int
    tipo: TipoViaje
    estado: EstadoViaje
    fecha: date
    origen: LugarResumen | None
    destino: LugarResumen | None
    hora_salida_programada: time | None
    hora_llegada_programada: time | None
    distancia_km: float | None
    km_reportado: float | None
    hora_llegada: time | None
    terminado_at: datetime | None
    notas_admin: str | None
    notas_operador: str | None
    mercancias: list[ViajeMercanciaOut]
    acuses: list[AcuseOut]
    acuse_requerido: bool
    acuse_completo: bool


# --- Servicio ----------------------------------------------------------------
class ServicioCreate(BaseModel):
    cliente_id: uuid.UUID
    unidad_id: uuid.UUID
    operador_id: uuid.UUID
    fecha: date
    subtotal: Decimal | None = None
    notas: str | None = None
    timbrado_anticipado: bool = False
    viajes: list[ViajeCreate]

    @model_validator(mode="after")
    def _check(self) -> "ServicioCreate":
        if not self.viajes:
            raise ValueError("Un servicio necesita al menos un viaje")
        if self.timbrado_anticipado and not (self.subtotal and self.subtotal > 0):
            raise ValueError("timbrado_anticipado exige subtotal > 0")
        return self


class ServicioUpdate(BaseModel):
    unidad_id: uuid.UUID | None = None
    operador_id: uuid.UUID | None = None
    fecha: date | None = None
    subtotal: Decimal | None = None
    notas: str | None = None
    timbrado_anticipado: bool | None = None


class ClienteResumen(BaseModel):
    id: uuid.UUID
    nombre_comercial: str
    modo_acuse: str
    regimen_receptor: str


class UnidadResumen(BaseModel):
    id: uuid.UUID
    apodo: str
    tipo_medidor: str
    num_barras: int | None


class OperadorResumen(BaseModel):
    id: uuid.UUID
    nombre: str


class ServicioDetalleOut(BaseModel):
    id: uuid.UUID
    numero: int
    fecha: date
    estado: EstadoServicio
    estado_facturacion: EstadoFacturacion
    timbrado_anticipado: bool
    cliente: ClienteResumen
    unidad: UnidadResumen
    operador: OperadorResumen
    subtotal: Decimal | None
    notas: str | None
    viajes: list[ViajeOut]
    factura_vigente: dict | None = None
    datos_fiscales_bloqueados: bool
    acciones_permitidas: list[str]
    # Fase 3 — `OperatorReportCard` (`05 §5`, H3.7). `None`/`[]` hasta que el operador
    # registre la inspección/cierre; el router los llena vía `operacion.service`.
    inspeccion: dict | None = None
    cierre: dict | None = None
    cargas: list[dict] = []
    combustible_total: dict | None = None
    # Solo poblado en `GET /operador/servicios` (`03 §7`): catálogo del cliente sin
    # claves SAT, para que el operador elija por nombre.
    mercancias_cliente: list[dict] | None = None


class ServicioListItemOut(BaseModel):
    id: uuid.UUID
    numero: int
    fecha: date
    estado: EstadoServicio
    estado_facturacion: EstadoFacturacion
    timbrado_anticipado: bool
    cliente: str
    unidad_apodo: str
    operador_nombre: str
    ruta_resumen: str
    viajes_total: int
    viajes_terminados: int
    acuses_requeridos: int
    acuses_completos: int
    subtotal: Decimal | None


class ConteosOut(BaseModel):
    programados: int
    en_curso: int
    por_facturar: int
    facturados: int
    cancelados: int


class DuplicarServicioIn(BaseModel):
    fecha: date


class CancelarServicioIn(BaseModel):
    motivo: str


class OrdenViajesIn(BaseModel):
    viaje_ids: list[uuid.UUID]


class TerminarViajeIn(BaseModel):
    mercancias: list[ViajeMercanciaIn] | None = None
    hora_llegada: time | None = None
    notas_operador: str | None = None
    referencia_acuse: str | None = None
    client_action_id: uuid.UUID | None = None


class AcuseReferenciaIn(BaseModel):
    referencia: str


class DistanciaSugeridaOut(BaseModel):
    distancia_km: float | None
    fuente: Literal["ultimo_viaje"] | None
