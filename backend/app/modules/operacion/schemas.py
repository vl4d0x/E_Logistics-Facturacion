"""DTOs de operación en campo — `03-api-contract §7`."""
import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, model_validator

from app.modules.servicios.schemas import ViajeMercanciaIn


class ChecklistIn(BaseModel):
    unidad_limpia: bool
    fumigacion_vigente: bool
    botiquin: bool
    casco_chaleco: bool
    aceite_ok: bool
    anticongelante_ok: bool
    neumaticos_ok: bool
    extintor_ok: bool


class IniciarServicioIn(BaseModel):
    client_action_id: uuid.UUID
    realizada_at: datetime
    checklist: ChecklistIn
    observaciones: str | None = None
    lectura_medidor: dict
    odometro_km: int | None = None


class TerminarViajeOperadorIn(BaseModel):
    client_action_id: uuid.UUID
    terminado_at: datetime
    hora_llegada: time | None = None
    notas: str | None = None
    mercancias: list[ViajeMercanciaIn] = []
    referencia_acuse: str | None = None


class KmPorViajeIn(BaseModel):
    viaje_id: uuid.UUID
    km: float


class CargaIn(BaseModel):
    id: uuid.UUID  # generado en el teléfono
    litros: Decimal
    precio_litro: Decimal
    importe: Decimal
    tipo_combustible: str | None = None
    cargada_at: datetime

    @model_validator(mode="after")
    def _check(self) -> "CargaIn":
        if self.litros <= 0 or self.precio_litro <= 0 or self.importe <= 0:
            raise ValueError("litros, precio_litro e importe deben ser mayores a 0")
        calculado = self.litros * self.precio_litro
        if abs(calculado - self.importe) > Decimal("1.00"):
            raise ValueError("litros × precio_litro no cuadra con importe (±$1.00)")
        return self


class CargaUpdate(BaseModel):
    """Corrección del admin (`03 §6`) — nunca toca `km_reportado`, eso es del operador."""

    litros: Decimal | None = None
    precio_litro: Decimal | None = None
    importe: Decimal | None = None
    tipo_combustible: str | None = None


class CerrarServicioIn(BaseModel):
    client_action_id: uuid.UUID
    cerrado_at: datetime
    km_por_viaje: list[KmPorViajeIn]
    lectura_medidor: dict
    odometro_km: int | None = None
    observaciones: str | None = None
    cargo_combustible: bool
    cargas: list[CargaIn] = []
