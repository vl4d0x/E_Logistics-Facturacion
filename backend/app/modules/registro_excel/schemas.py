import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

CP_GENERICO = "50000"  # Toluca, Estado de México: CP de los destinos que no están en el catálogo


class NuevoLugarIn(BaseModel):
    """Destino que no está en el catálogo: se da de alta con RFC genérico, Estado de México, 70 km."""

    nombre: str
    codigo_postal: str = CP_GENERICO

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = " ".join(v.split()).upper()
        if not v:
            raise ValueError("Escribe el nombre del lugar")
        return v

    @field_validator("codigo_postal")
    @classmethod
    def _cp(cls, v: str) -> str:
        v = str(v).strip()
        if not (len(v) == 5 and v.isdigit()):
            raise ValueError("El código postal debe tener 5 dígitos")
        return v


class LugarElegidoIn(BaseModel):
    texto_excel: str | None = None  # lo que decía el Excel (para recordar la elección)
    lugar_id: uuid.UUID | None = None
    nuevo: NuevoLugarIn | None = None

    @model_validator(mode="after")
    def _uno(self) -> "LugarElegidoIn":
        if (self.lugar_id is None) == (self.nuevo is None):
            raise ValueError("Elige un lugar del catálogo o da de alta uno nuevo")
        return self


class MercanciaDestinoIn(BaseModel):
    mercancia_frecuente_id: uuid.UUID
    peso_kg: float
    cantidad: Decimal = Decimal(1)

    @field_validator("peso_kg")
    @classmethod
    def _peso(cls, v: float) -> float:
        if not v or v <= 0:
            raise ValueError("Los kg deben ser mayores a cero")
        return v


class DestinoIn(LugarElegidoIn):
    folio: str | None = None  # REF del cliente (clientes con acuse por referencia)
    sin_acuse: bool = False  # el destino no tiene REF ni escaneo
    distancia_km: float | None = None
    mercancias: list[MercanciaDestinoIn] = []


class CrearDesdeFilaIn(BaseModel):
    cliente_id: uuid.UUID
    unidad_id: uuid.UUID
    operador_id: uuid.UUID
    fecha: date
    subtotal: Decimal | None = None
    origen: LugarElegidoIn
    destinos: list[DestinoIn]

    @model_validator(mode="after")
    def _destinos(self) -> "CrearDesdeFilaIn":
        if not self.destinos:
            raise ValueError("El servicio necesita al menos un destino")
        return self
