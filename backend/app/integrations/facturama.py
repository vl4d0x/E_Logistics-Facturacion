"""Cliente HTTP de Facturama (PAC). Basic Auth, base URL según `FACTURAMA_ENV`.

Endpoints verificados contra la doc oficial de Facturama (sandbox), ver
`backend/NOTES.md` para el detalle y las fuentes:
    POST   /3/cfdis                                  → crear/timbrar CFDI
    GET    /api/Cfdi/{format}/{type}/{id}             → descargar pdf|xml|html
    DELETE /cfdi/{cfdiId}?type=&motive=&uuidReplacement=  → cancelar

`type` para descarga/cancelación en un emisor único es "issued" (nosotros
siempre emitimos, nunca recibimos).
"""
from typing import Any, Literal, Self

import httpx

from app.core.config import get_settings

_SANDBOX_BASE_URL = "https://apisandbox.facturama.mx"
_PRODUCTION_BASE_URL = "https://api.facturama.mx"

FileFormat = Literal["pdf", "xml", "html"]


class FacturamaError(Exception):
    """Error del PAC (Facturama). El mensaje viene del PAC cuando está disponible."""

    def __init__(self, message: str, status_code: int | None = None, raw: Any = None) -> None:
        self.status_code = status_code
        self.raw = raw
        super().__init__(message)


class FacturamaClient:
    def __init__(self, timeout: float = 30.0) -> None:
        settings = get_settings()
        base_url = _PRODUCTION_BASE_URL if settings.facturama_env == "production" else _SANDBOX_BASE_URL

        if not settings.facturama_user or not settings.facturama_password:
            raise FacturamaError(
                "Faltan FACTURAMA_USER / FACTURAMA_PASSWORD en el entorno (backend/.env)."
            )

        self._client = httpx.Client(
            base_url=base_url,
            auth=(settings.facturama_user, settings.facturama_password),
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def create_cfdi(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea y timbra un CFDI. Devuelve el CFDI timbrado (incluye `Id`, `Complement.TaxStamp.Uuid`)."""
        response = self._client.post("/3/cfdis", json=payload)
        return self._parse(response)

    def get_file(self, cfdi_id: str, fmt: FileFormat) -> dict[str, Any]:
        """Descarga el archivo del CFDI. Respuesta: {ContentEncoding, ContentType, ContentLength, Content(base64)}."""
        response = self._client.get(f"/api/Cfdi/{fmt}/issued/{cfdi_id}")
        return self._parse(response)

    def resolve_postal_code(self, cp: str) -> dict[str, Any] | None:
        """`GET /Catalogs/PostalCodes?keyword={cp}` -> {StateCode, MunicipalityCode, LocationCode}.

        Hace falta para `Domicilio.Municipio`/`Localidad` de Carta Porte (claves
        numéricas del catálogo SAT, no texto libre) -- ver `backend/NOTES.md`.
        """
        response = self._client.get("/Catalogs/PostalCodes", params={"keyword": cp})
        data = self._parse(response)
        if not data:
            return None
        return data[0]

    def cancel_cfdi(
        self, cfdi_id: str, motive: str, uuid_replacement: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, str] = {"type": "issued", "motive": motive}
        if uuid_replacement:
            params["uuidReplacement"] = uuid_replacement
        response = self._client.delete(f"/cfdi/{cfdi_id}", params=params)
        return self._parse(response)

    @staticmethod
    def _parse(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.is_error:
            message = data.get("Message") or data.get("message") or str(data)
            raise FacturamaError(message, status_code=response.status_code, raw=data)

        return data
