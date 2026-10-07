"""Payload del REP (CFDI tipo P, Pagos 2.0) para Facturama — `06-cobranza-rep §4-5`. Puro, sin red ni DB.

Estructura según el mapeo de Facturama (`Complemento.Payments[].RelatedDocuments[]`); el
comprobante raíz de tipo P NO lleva `Items`, `PaymentForm`, `PaymentMethod` ni `Currency`.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

TASA_IVA = Decimal("0.16")
TASA_RETENCION = Decimal("0.04")
_CENTAVO = Decimal("0.01")


def _r(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ImpuestosParcialidad:
    base: Decimal
    traslado: Decimal
    retencion: Decimal


def impuestos_proporcionales(
    *,
    subtotal: Decimal,
    total: Decimal,
    iva_trasladado: Decimal,
    iva_retenido: Decimal,
    pagado: Decimal,
    saldo_insoluto: Decimal,
    previas: list[ImpuestosParcialidad],
    receptor_moral: bool,
) -> ImpuestosParcialidad:
    """Impuestos de una parcialidad (§5): la suma de todas reproduce exactamente los de la factura."""
    if pagado == total and not previas:
        return ImpuestosParcialidad(subtotal, iva_trasladado, iva_retenido)
    if saldo_insoluto == 0:  # última parcialidad: absorbe el redondeo
        return ImpuestosParcialidad(
            subtotal - sum((p.base for p in previas), Decimal(0)),
            iva_trasladado - sum((p.traslado for p in previas), Decimal(0)),
            iva_retenido - sum((p.retencion for p in previas), Decimal(0)),
        )
    base = _r(pagado * subtotal / total)
    return ImpuestosParcialidad(
        base,
        _r(base * TASA_IVA),
        _r(base * TASA_RETENCION) if receptor_moral else Decimal("0.00"),
    )


@dataclass(frozen=True)
class DocumentoRelacionado:
    uuid: str
    serie: str | None
    folio: str | None
    num_parcialidad: int
    saldo_anterior: Decimal
    pagado: Decimal
    saldo_insoluto: Decimal
    impuestos: ImpuestosParcialidad


def _dos(valor: Decimal) -> str:
    return f"{valor:.2f}"


def _impuestos_dr(imp: ImpuestosParcialidad) -> list[dict[str, Any]]:
    taxes = [
        {
            "Name": "IVA",
            "Rate": "0.16",
            "Total": _dos(imp.traslado),
            "Base": _dos(imp.base),
            "IsRetention": "false",
            "IsFederalTax": "true",
        }
    ]
    if imp.retencion > 0:
        taxes.append(
            {
                "Name": "IVA RET",
                "Rate": "0.04",
                "Total": _dos(imp.retencion),
                "Base": _dos(imp.base),
                "IsRetention": "true",
                "IsFederalTax": "true",
            }
        )
    return taxes


def construir_payload_rep(
    *,
    serie: str | None,
    expedition_place: str,
    receptor: dict[str, str],
    pago: dict[str, Any],
    documentos: list[DocumentoRelacionado],
) -> dict[str, Any]:
    """`receptor`: razon_social, rfc, cp_fiscal, regimen_fiscal. `pago`: fecha (datetime), forma_pago,
    monto (Decimal), y opcionales num_operacion, rfc_emisor_cta_ord, cta_ordenante, rfc_emisor_cta_ben,
    cta_beneficiario."""
    related = []
    for d in documentos:
        doc: dict[str, Any] = {
            "Uuid": d.uuid,
            "PaymentMethod": "PPD",
            "PartialityNumber": str(d.num_parcialidad),
            "PreviousBalanceAmount": _dos(d.saldo_anterior),
            "AmountPaid": _dos(d.pagado),
            "ImpSaldoInsoluto": _dos(d.saldo_insoluto),
            "TaxObject": "02",
            "Currency": "MXN",
            "EquivalenceDocRel": "1",
            "Taxes": _impuestos_dr(d.impuestos),
        }
        if d.serie:
            doc["Serie"] = d.serie
        if d.folio:
            doc["Folio"] = d.folio
        related.append(doc)

    payment: dict[str, Any] = {
        "Date": pago["fecha"].strftime("%Y-%m-%dT%H:%M:%S"),
        "PaymentForm": pago["forma_pago"],
        "Amount": _dos(pago["monto"]),
        "Currency": "MXN",
        "RelatedDocuments": related,
    }
    for origen, destino in (
        ("num_operacion", "OperationNumber"),
        ("rfc_emisor_cta_ord", "AccountOrderRfc"),
        ("cta_ordenante", "AccountOrderNumber"),
        ("rfc_emisor_cta_ben", "AccountBeneficiaryRfc"),
        ("cta_beneficiario", "AccountBeneficiaryNumber"),
    ):
        if pago.get(origen):
            payment[destino] = pago[origen]

    payload: dict[str, Any] = {
        "CfdiType": "P",
        "ExpeditionPlace": expedition_place,
        "Receiver": {
            "Rfc": receptor["rfc"],
            "Name": receptor["razon_social"],
            "CfdiUse": "CP01",
            "FiscalRegime": receptor["regimen_fiscal"],
            "TaxZipCode": receptor["cp_fiscal"],
        },
        "Complemento": {"Payments": [payment]},
    }
    if serie:
        payload["Serie"] = serie
    return payload


def fecha_vencimiento_rep(fecha_pago: datetime):
    """Día 5 del mes siguiente; si cae en fin de semana, el lunes siguiente (`06 §7`)."""
    from datetime import date, timedelta

    anio, mes = (fecha_pago.year + 1, 1) if fecha_pago.month == 12 else (fecha_pago.year, fecha_pago.month + 1)
    vence = date(anio, mes, 5)
    while vence.weekday() >= 5:
        vence += timedelta(days=1)
    return vence
