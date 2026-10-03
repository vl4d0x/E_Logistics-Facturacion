"""Validación de `lectura_medidor` contra la unidad — `fase-3 H3.5`, `02 §3.11`."""
from decimal import Decimal

from app.core.errors import AppError
from app.modules.catalogos.models import Unidad


def validar_lectura_medidor(lectura: dict, unidad: Unidad) -> Decimal:
    """Valida la lectura cruda del medidor contra el tipo/barras de la unidad y
    devuelve `nivel_combustible` (0.000-1.000). Lanza 422 si no cuadra."""
    tipo = lectura.get("tipo")
    if tipo != unidad.tipo_medidor.value:
        raise AppError(
            "validation_error",
            f"El medidor de esta unidad es de tipo '{unidad.tipo_medidor.value}', no '{tipo}'",
            422,
            details=[{"field": "lectura_medidor.tipo", "issue": "no coincide con la unidad"}],
        )

    if tipo == "aguja":
        octavos = lectura.get("octavos")
        if not isinstance(octavos, int) or not (0 <= octavos <= 8):
            raise AppError(
                "validation_error",
                "octavos debe ser un entero entre 0 y 8",
                422,
                details=[{"field": "lectura_medidor.octavos"}],
            )
        return Decimal(octavos) / Decimal(8)

    # barras
    total = lectura.get("total")
    barras = lectura.get("barras")
    if total != unidad.num_barras:
        raise AppError(
            "validation_error",
            f"La unidad tiene {unidad.num_barras} barras, no {total}. "
            "Si se reconfiguró, actualiza el catálogo y vuelve a marcar.",
            422,
            details=[{"field": "lectura_medidor.total", "issue": "no coincide con la unidad"}],
        )
    if not isinstance(barras, int) or not isinstance(total, int) or not (0 <= barras <= total):
        raise AppError(
            "validation_error",
            "barras debe ser un entero entre 0 y el total de la unidad",
            422,
            details=[{"field": "lectura_medidor.barras"}],
        )
    return Decimal(barras) / Decimal(total)
