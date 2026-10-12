"""DTOs de facturación — `03-api-contract §9`."""
import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.modules.catalogos.models import RegimenReceptor


class ImpuestosPreviewIn(BaseModel):
    regimen_receptor: RegimenReceptor
    subtotal: Decimal | None = None
    total: Decimal | None = None

    @model_validator(mode="after")
    def _uno_u_otro(self) -> "ImpuestosPreviewIn":
        if (self.subtotal is None) == (self.total is None):
            raise ValueError("Manda subtotal o total, no ambos ni ninguno")
        return self


class MontosOut(BaseModel):
    subtotal: Decimal
    iva_trasladado: Decimal
    iva_retenido: Decimal
    total: Decimal


class ValidacionCheck(BaseModel):
    regla: str
    nivel: str  # "ok" | "warning" | "error"
    mensaje: str
    campo: str | None = None


class ValidacionOut(BaseModel):
    ok: bool
    checks: list[ValidacionCheck]
    preview: MontosOut | None


# --- Pantalla "Facturar" (`03-api-contract §9`, H4.4) ---


class ReceptorOut(BaseModel):
    razon_social: str
    rfc: str
    cp_fiscal: str
    regimen_fiscal: str
    regimen_receptor: RegimenReceptor
    uso_cfdi: str
    metodo_pago: str
    forma_pago: str = "99"


class FolioViajeOut(BaseModel):
    viaje_id: uuid.UUID
    destino: str
    folio: str | None = None


class ConceptoOut(BaseModel):
    clave_prod_serv: str = "78101802"
    clave_unidad: str = "SX"
    descripcion: str
    descripcion_autogenerada: bool
    requiere_folio: bool = False
    folio_cliente: str | None = None
    folios: list[FolioViajeOut] = []  # un folio por destino (clientes que lo exigen en el concepto)


class DesgloseDestinoOut(BaseModel):
    viaje_id: uuid.UUID
    destino: str
    monto: Decimal | None = None
    capturado: bool  # False = monto implícito (un solo destino se lleva todo el subtotal)


class DesgloseDestinoIn(BaseModel):
    viaje_id: uuid.UUID
    monto: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class UbicacionOut(BaseModel):
    id_ubicacion: str
    tipo: str  # "Origen" | "Destino"
    viaje_id: uuid.UUID
    viaje_tipo: str | None = None  # recoleccion | entrega | recoleccion_entrega
    lugar: dict
    fecha_hora: datetime | None
    fecha_hora_fuente: str  # "real" | "programada"
    hora_programada: time | None = None  # editable en la pantalla Facturar
    distancia_km: float | None
    km_reportado: float | None


class MercanciaFacturarOut(BaseModel):
    viaje_id: uuid.UUID
    id: uuid.UUID | None = None
    mercancia_frecuente_id: uuid.UUID | None = None
    descripcion: str
    bienes_transp: str
    clave_unidad: str
    cantidad: Decimal
    peso_kg: float


class AutotransporteOut(BaseModel):
    apodo: str
    placa: str
    config_vehicular: str
    peso_bruto_vehicular: float
    anio_modelo: int | None
    perm_sct: str
    num_permiso_sct: str
    aseguradora: str | None
    poliza: str | None


class FiguraOut(BaseModel):
    nombre: str
    rfc: str
    num_licencia: str


class DesgloseLineaOut(BaseModel):
    concepto: str
    monto: Decimal


class PrecioSugeridoOut(BaseModel):
    monto: Decimal | None
    desglose: list[DesgloseLineaOut]
    confianza: str | None
    fuente: str | None
    explicacion: str
    referencias: list[int]
    ultimos_precios_ruta: list[dict]
    rango: tuple[Decimal, Decimal] | None
    configuracion_pendiente: bool


class AcuseFacturarOut(BaseModel):
    viaje_id: uuid.UUID
    tipo: str
    url: str | None = None
    mime: str | None = None
    referencia: str | None = None
    pagina: int


class FacturacionDetalleOut(BaseModel):
    cliente_id: uuid.UUID | None = None
    unidad_id: uuid.UUID | None = None
    operador_id: uuid.UUID | None = None
    modo: str  # "normal" | "anticipado"
    timbrado_modo: str = "precio"  # "precio" | "cero" (timbra con $0.10 y se cancela sola)
    servicio_id: uuid.UUID
    receptor: ReceptorOut
    concepto: ConceptoOut
    desglose_precio: list[DesgloseDestinoOut] = []
    ubicaciones: list[UbicacionOut]
    mercancias: list[MercanciaFacturarOut]
    autotransporte: AutotransporteOut
    figura: FiguraOut
    montos: MontosOut | None
    precio_sugerido: PrecioSugeridoOut
    acuses: list[AcuseFacturarOut]
    validacion: ValidacionOut
    facturama_configurado: bool


class FacturacionUpdateIn(BaseModel):
    subtotal: Decimal | None = None
    descripcion_concepto: str | None = None
    folio_cliente: str | None = None
    uso_cfdi: str | None = None
    metodo_pago: str | None = None


class FacturarIn(BaseModel):
    total_esperado: Decimal
