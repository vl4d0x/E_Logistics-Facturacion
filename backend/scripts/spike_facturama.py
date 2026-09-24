"""H0.5 — Spike de Facturama (de-risk).

Arma un CFDI 4.0 tipo Ingreso + Complemento Carta Porte 3.1 con datos
INVENTADOS PERO VÁLIDOS y lo timbra contra el sandbox de Facturama, para
validar el mapeo temprano (ver `00-overview §0` sobre datos ficticios: NUNCA
usar estos datos, ni parecidos, para timbrar en real).

La estructura del payload está verificada contra la doc oficial de Facturama
— ver `backend/NOTES.md` para el detalle y las fuentes.

Requiere FACTURAMA_USER / FACTURAMA_PASSWORD en el entorno (backend/.env).
Sin ellas, el script se detiene con un mensaje claro (no inventa credenciales).

Uso:
    cd backend && python -m scripts.spike_facturama
"""
import json
import sys
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import get_settings
from app.integrations.facturama import FacturamaClient, FacturamaError

# --- Datos ficticios rotulados — NO son datos reales de Elogistics ---
_SUBTOTAL = Decimal("1650.00")
_IVA_TRASLADADO = (_SUBTOTAL * Decimal("0.16")).quantize(Decimal("0.01"), ROUND_HALF_UP)
_IVA_RETENIDO = (_SUBTOTAL * Decimal("0.04")).quantize(Decimal("0.01"), ROUND_HALF_UP)
_TOTAL = _SUBTOTAL + _IVA_TRASLADADO - _IVA_RETENIDO


def build_payload() -> dict:
    """Construye el payload. Ver `04-facturacion-cfdi §1-4` y `backend/NOTES.md`."""
    return {
        "Serie": "SPIKE",
        "CfdiType": "I",
        "PaymentForm": "99",  # "Por definir" — ficticio para el spike (04 §7, pendiente confirmar)
        "ExpeditionPlace": "52176",  # CP ficticio, mismo patrón que el ejemplo real (04 §1)
        "PaymentMethod": "PPD",
        "Currency": "MXN",
        "Exportation": "01",
        "Receiver": {
            "Name": "CLIENTE DE PRUEBA SPIKE SA DE CV",
            "CfdiUse": "G03",
            "Rfc": "EKU9003173C9",  # RFC genérico de pruebas públicas del SAT/Facturama
            "FiscalRegime": "601",
            "TaxZipCode": "52000",
        },
        "Issuer": {},  # sandbox usa el emisor/CSD demo de la cuenta — ver NOTES.md
        "Items": [
            {
                "Quantity": "1",
                "ProductCode": "78101802",  # constante — servicios de transporte de carga
                "UnitCode": "SX",
                "Unit": "Envío",
                "Description": (
                    "FLETE UNIDAD CAMIONETA SPIKE (FICTICIA)\n"
                    "ORIGEN: TOLUCA, MEX (FICTICIO)\n"
                    "DESTINO: METEPEC, MEX (FICTICIO)\n"
                    "FECHA: 2026-09-23"
                ),
                "UnitPrice": str(_SUBTOTAL),
                "Subtotal": str(_SUBTOTAL),
                "TaxObject": "02",
                "Taxes": [
                    {
                        "Name": "IVA",
                        "Rate": "0.16",
                        "Total": str(_IVA_TRASLADADO),
                        "Base": str(_SUBTOTAL),
                        "IsRetention": "false",
                        "IsFederalTax": "true",
                    },
                    {
                        "Name": "IVA RET",
                        "Rate": "0.04",
                        "Total": str(_IVA_RETENIDO),
                        "Base": str(_SUBTOTAL),
                        "IsRetention": "true",
                        "IsFederalTax": "true",
                    },
                ],
                "Total": str(_TOTAL),
            }
        ],
        "Complemento": {
            "CartaPorte31": {
                "TranspInternac": "No",
                "TotalDistRec": "80",
                "Ubicaciones": [
                    {
                        "TipoUbicacion": "Origen",
                        "IDUbicacion": "OR000001",
                        "RFCRemitenteDestinatario": "EKU9003173C9",
                        "NombreRemitenteDestinatario": "CLIENTE DE PRUEBA SPIKE SA DE CV",
                        "FechaHoraSalidaLlegada": "2026-09-23T08:00:00",
                        "Domicilio": {
                            "Pais": "MEX",
                            "CodigoPostal": "52000",
                            "Estado": "MEX",
                            "Municipio": "106",  # clave SAT ficticia (Toluca) — verificar catálogo real en Fase 4
                        },
                    },
                    {
                        "TipoUbicacion": "Destino",
                        "IDUbicacion": "DE000001",
                        "RFCRemitenteDestinatario": "XAXX010101000",  # genérico
                        "NombreRemitenteDestinatario": "DESTINATARIO DE PRUEBA (FICTICIO)",
                        "FechaHoraSalidaLlegada": "2026-09-23T10:00:00",
                        "DistanciaRecorrida": "80",
                        "Domicilio": {
                            "Pais": "MEX",
                            "CodigoPostal": "52140",
                            "Estado": "MEX",
                            "Municipio": "054",  # clave SAT ficticia (Metepec) — verificar catálogo real en Fase 4
                        },
                    },
                ],
                "Mercancias": {
                    "PesoBrutoTotal": "20",
                    "UnidadPeso": "KGM",
                    "NumTotalMercancias": "1",
                    "Mercancia": [
                        {
                            "BienesTransp": "12164501",
                            "Descripcion": "Mercancía de prueba spike (ficticia)",
                            "Cantidad": "1.0",
                            "ClaveUnidad": "X4G",
                            "Unidad": "Caja de cartón",
                            "PesoEnKg": "20",
                        }
                    ],
                    "Autotransporte": {
                        "PermSCT": "TPAF01",
                        "NumPermisoSCT": "SPIKE0001",
                        "IdentificacionVehicular": {
                            "ConfigVehicular": "C2",
                            "PesoBrutoVehicular": "8",  # toneladas — ojo, no kg (04 §5)
                            "PlacaVM": "SPK0001",
                            "AnioModeloVM": "2022",
                        },
                        "Seguros": {
                            "AseguraRespCivil": "Aseguradora de Prueba Spike",
                            "PolizaRespCivil": "SPIKE-POLIZA-0001",
                        },
                    },
                },
                "FiguraTransporte": [
                    {
                        "TipoFigura": "01",
                        "RFCFigura": "XAXX010101000",  # genérico — operador ficticio
                        "NumLicencia": "SPIKE-LIC-0001",
                        "NombreFigura": "OPERADOR DE PRUEBA SPIKE",
                    }
                ],
            }
        },
    }


def main() -> None:
    settings = get_settings()

    if not settings.facturama_user or not settings.facturama_password:
        print(
            "🔴 Faltan FACTURAMA_USER / FACTURAMA_PASSWORD en el entorno.\n"
            "   Pídele a Vlad las credenciales del sandbox de Facturama, ponlas en\n"
            "   backend/.env (ver .env.example) y vuelve a correr este script.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    payload = build_payload()
    print(f"→ Timbrando contra FACTURAMA_ENV={settings.facturama_env} ...")

    try:
        with FacturamaClient() as client:
            result = client.create_cfdi(payload)
    except FacturamaError as exc:
        print("✗ Error del PAC (Facturama):", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        if exc.raw is not None:
            print(json.dumps(exc.raw, indent=2, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc

    uuid_fiscal = result.get("Complement", {}).get("TaxStamp", {}).get("Uuid")
    cfdi_id = result.get("Id")
    print("✅ Timbrado OK")
    print(f"   Id Facturama: {cfdi_id}")
    print(f"   UUID fiscal:  {uuid_fiscal}")


if __name__ == "__main__":
    main()
