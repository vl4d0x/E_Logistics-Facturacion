"""DTOs de facturación — `03-api-contract §9`."""
from decimal import Decimal

from pydantic import BaseModel, model_validator

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
