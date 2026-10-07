"""Paso 0 de la Fase 5 — spike del REP contra el sandbox de Facturama (`fase-5 Paso 0`).

Timbra un REP de pago total y otro de dos parcialidades sobre un CFDI de PRUEBA (receptor
ficticio del SAT, nunca un cliente). Requiere el UUID de un CFDI timbrado en el sandbox.

Uso:  cd backend && python -m scripts.spike_rep <uuid_cfdi_de_prueba> [serie]
"""
import json
import sys
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.integrations.facturama import FacturamaClient, FacturamaError
from app.modules.cobranza.rep_payload import (
    DocumentoRelacionado,
    construir_payload_rep,
    impuestos_proporcionales,
)

D = Decimal
FACTURA = {"subtotal": D("1650.00"), "total": D("1848.00"), "iva_trasladado": D("264.00"), "iva_retenido": D("66.00")}
RECEPTOR = {  # datos públicos del RFC de pruebas del SAT
    "razon_social": "ESCUELA KEMPER URGATE", "rfc": "EKU9003173C9", "cp_fiscal": "42501", "regimen_fiscal": "601",
}


def _rep(uuid_cfdi: str, serie: str | None, pagado: D, saldo_ant: D, num: int, previas: list) -> tuple[dict, object]:
    saldo = saldo_ant - pagado
    imp = impuestos_proporcionales(**FACTURA, pagado=pagado, saldo_insoluto=saldo, previas=previas, receptor_moral=True)
    doc = DocumentoRelacionado(uuid_cfdi, "SPIKE", "6", num, saldo_ant, pagado, saldo, imp)
    payload = construir_payload_rep(
        serie=serie,
        expedition_place=get_settings().emisor_lugar_expedicion or "52176",
        receptor=RECEPTOR,
        pago={"fecha": datetime.now(ZoneInfo("America/Mexico_City")).replace(microsecond=0, tzinfo=None), "forma_pago": "03", "monto": pagado},
        documentos=[doc],
    )
    return payload, imp


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    settings = get_settings()
    if settings.facturama_env != "sandbox":
        raise SystemExit("Solo corre contra el sandbox.")
    uuid_cfdi = sys.argv[1]
    serie = sys.argv[2] if len(sys.argv) > 2 else None
    with FacturamaClient() as client:
        previas: list = []
        saldo = FACTURA["total"]
        for num, pagado in enumerate([D("1000.00"), D("848.00")], start=1):
            payload, imp = _rep(uuid_cfdi, serie, pagado, saldo, num, previas)
            try:
                r = client.create_cfdi(payload)
            except FacturamaError as exc:
                print(f"✗ parcialidad {num}: {exc}")
                print(json.dumps(exc.raw, indent=2, ensure_ascii=False)[:1500])
                print(json.dumps(payload, indent=2, ensure_ascii=False)[:1500])
                raise SystemExit(1) from exc
            print(f"✅ REP parcialidad {num} (${pagado}) | Id={r.get('Id')} UUID={r['Complement']['TaxStamp']['Uuid']}")
            previas.append(imp)
            saldo -= pagado


if __name__ == "__main__":
    main()
