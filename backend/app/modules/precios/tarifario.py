"""Tarifario fijo por cliente (hoy solo Chemital) — nivel 1 del sugeridor.

Puro: sin DB. Regla confirmada por Vlad (2026-10-05): el primer destino en CDMX se
cobra con la tarifa de la unidad (`cdmx`); cada destino/tiro adicional del servicio
se cobra con su tarifa de `extra`. La unidad se clasifica por tonelaje, no por apodo.
Los valores viven en `configuracion` (`precio.tarifario_cliente`) y se editan desde la UI.
"""
from dataclasses import dataclass
from decimal import Decimal

TIERS = ("saveiro", "nissan", "ram")


def cp_es_cdmx(cp: str | None) -> bool:
    """CDMX ocupa los CP 01000–16999."""
    if not cp or not cp.strip().isdigit() or len(cp.strip()) != 5:
        return False
    return 1000 <= int(cp) <= 16999


def tier_de_unidad(peso_bruto_ton: float | None) -> str | None:
    """Saveiro 0.5 t, Nissan 1 t, Ram 3.5 t. Más pesada (Rabón) no tiene tarifa."""
    if peso_bruto_ton is None:
        return None
    if peso_bruto_ton <= 0.5:
        return "saveiro"
    if peso_bruto_ton <= 1:
        return "nissan"
    if peso_bruto_ton <= 3.5:
        return "ram"
    return None


@dataclass
class LineaTarifa:
    concepto: str
    monto: Decimal


def cliente_aplica(tarifario: dict | None, nombres_cliente: list[str]) -> bool:
    if not tarifario:
        return False
    patron = str(tarifario.get("cliente", "")).strip().lower()
    return bool(patron) and any(patron in n.lower() for n in nombres_cliente)


def calcular(tarifario: dict, tier: str | None, cps_destinos: list[str | None]) -> list[LineaTarifa] | None:
    """Líneas del desglose, o None si la regla no aplica (sin tarifa, sin destino en CDMX)."""
    if tier is None or not any(cp_es_cdmx(cp) for cp in cps_destinos):
        return None
    tarifa = (tarifario.get("tarifas") or {}).get(tier)
    if not tarifa:
        return None
    base, extra = Decimal(str(tarifa["cdmx"])), Decimal(str(tarifa["extra"]))
    lineas = [LineaTarifa(f"Viaje a CDMX · {tier.capitalize()}", base)]
    n_extra = len(cps_destinos) - 1
    if n_extra > 0:
        lineas.append(LineaTarifa(f"{n_extra} destino(s) adicional(es) × ${extra:,.2f}", extra * n_extra))
    return lineas
