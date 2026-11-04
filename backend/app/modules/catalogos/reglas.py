"""Reglas de negocio sobre a quién se factura (Vlad, 3 nov 2026)."""

# RFC al que JAMÁS se le emite una factura → (nombre, RFC y nombre del cliente al que sí se factura).
# Los servicios de SAFMEX se facturan a LESAFFRE. Las facturas viejas a SAFMEX (del Facturador
# Electrónico) siguen existiendo y pueden recibir su REP; lo que se bloquea es timbrar facturas nuevas.
RFC_NO_FACTURABLES: dict[str, tuple[str, str, str]] = {
    "SAF810323HF8": ("SAFMEX", "LMA200417HY5", "LESAFFRE"),
}


def motivo_no_facturable(rfc: str | None) -> str | None:
    """Mensaje si a ese RFC no se le puede facturar; None si sí."""
    regla = RFC_NO_FACTURABLES.get((rfc or "").strip().upper())
    if regla is None:
        return None
    nombre, rfc_correcto, nombre_correcto = regla
    return f"Nunca se factura a {nombre} ({rfc}): este servicio se factura a {nombre_correcto} ({rfc_correcto})."
