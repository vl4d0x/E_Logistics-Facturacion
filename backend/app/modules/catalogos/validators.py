"""Validaciones compartidas de catálogos (RFC, etc.) — `fase-1-catalogos §Casos borde`."""
import re

# Persona moral: 3 letras + 6 dígitos (AAMMDD) + 3 alfanuméricos de homoclave = 12.
# Persona física: 4 letras + 6 dígitos + 3 alfanuméricos de homoclave = 13.
_RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")


def validate_rfc(rfc: str) -> str:
    rfc = rfc.strip().upper()
    if not _RFC_RE.match(rfc):
        raise ValueError("RFC inválido: debe tener el formato de 12 o 13 caracteres del SAT")
    return rfc


RFC_GENERICO_NACIONAL = "XAXX010101000"
RFC_GENERICO_EXTRANJERO = "XEXX010101000"


def validate_rfc_lugar(rfc: str) -> str:
    """RFC del remitente/destinatario de la Carta Porte. Todo el transporte es nacional, así
    que el genérico de extranjeros (XEXX…) no se acepta: el SAT lo rechaza al timbrar."""
    rfc = validate_rfc(rfc)
    if rfc == RFC_GENERICO_EXTRANJERO:
        raise ValueError(f"XEXX010101000 es para extranjeros; usa el RFC real o el genérico {RFC_GENERICO_NACIONAL}")
    return rfc
