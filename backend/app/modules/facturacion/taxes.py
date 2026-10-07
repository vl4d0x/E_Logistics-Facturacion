"""Cálculo de impuestos — `04-facturacion-cfdi §3-3.1`. Puro, sin red ni DB.

El backend es la verdad (`03-api-contract §9`, `total_esperado` en `/facturar`);
`frontend/src/lib/money.ts` replica esta misma función para feedback instantáneo.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from app.modules.catalogos.models import RegimenReceptor

TASA_IVA = Decimal("0.16")
TASA_RETENCION = Decimal("0.04")


class Montos(NamedTuple):
    subtotal: Decimal
    iva_trasladado: Decimal
    iva_retenido: Decimal
    total: Decimal


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_impuestos(subtotal: Decimal, regimen_receptor: RegimenReceptor) -> Montos:
    subtotal = _redondear(subtotal)
    iva_trasladado = _redondear(subtotal * TASA_IVA)
    iva_retenido = (
        _redondear(subtotal * TASA_RETENCION) if regimen_receptor == RegimenReceptor.moral else Decimal("0.00")
    )
    total = subtotal + iva_trasladado - iva_retenido
    return Montos(subtotal, iva_trasladado, iva_retenido, total)


def subtotal_desde_total(total: Decimal, regimen_receptor: RegimenReceptor) -> Decimal:
    factor = Decimal("1.12") if regimen_receptor == RegimenReceptor.moral else Decimal("1.16")
    return _redondear(total / factor)
