"""`06-cobranza-rep §4-5, §7` — payload del REP, impuestos proporcionales y vencimientos."""
from datetime import UTC, date, datetime
from decimal import Decimal

from app.modules.cobranza.rep_payload import (
    DocumentoRelacionado,
    ImpuestosParcialidad,
    construir_payload_rep,
    fecha_vencimiento_rep,
    impuestos_proporcionales,
)

D = Decimal
FACTURA = {"subtotal": D("1650.00"), "total": D("1848.00"), "iva_trasladado": D("264.00"), "iva_retenido": D("66.00")}


def test_pago_completo_reproduce_los_impuestos_de_la_factura():
    imp = impuestos_proporcionales(**FACTURA, pagado=D("1848.00"), saldo_insoluto=D("0"), previas=[], receptor_moral=True)
    assert (imp.base, imp.traslado, imp.retencion) == (D("1650.00"), D("264.00"), D("66.00"))


def test_parcialidades_suman_exactamente_los_impuestos_de_la_factura():
    pagos = [D("500.00"), D("700.00"), D("648.00")]
    previas: list[ImpuestosParcialidad] = []
    saldo = FACTURA["total"]
    for p in pagos:
        saldo -= p
        previas.append(
            impuestos_proporcionales(**FACTURA, pagado=p, saldo_insoluto=saldo, previas=list(previas), receptor_moral=True)
        )
    assert sum(i.base for i in previas) == FACTURA["subtotal"]
    assert sum(i.traslado for i in previas) == FACTURA["iva_trasladado"]
    assert sum(i.retencion for i in previas) == FACTURA["iva_retenido"]


def test_persona_fisica_no_lleva_retencion():
    imp = impuestos_proporcionales(
        subtotal=D("1000.00"), total=D("1160.00"), iva_trasladado=D("160.00"), iva_retenido=D("0.00"),
        pagado=D("580.00"), saldo_insoluto=D("580.00"), previas=[], receptor_moral=False,
    )
    assert imp.retencion == D("0.00") and imp.base == D("500.00") and imp.traslado == D("80.00")


def test_payload_un_pago_y_n_documentos():
    imp = ImpuestosParcialidad(D("1650.00"), D("264.00"), D("66.00"))
    docs = [
        DocumentoRelacionado("uuid-1", "ELG", "7", 1, D("1848.00"), D("1848.00"), D("0.00"), imp),
        DocumentoRelacionado("uuid-2", "ELG", "8", 1, D("1848.00"), D("1848.00"), D("0.00"), imp),
    ]
    p = construir_payload_rep(
        serie="REP",
        expedition_place="52176",
        receptor={"razon_social": "CHEMITAL DE MEXICO", "rfc": "CME091007LG1", "cp_fiscal": "52004", "regimen_fiscal": "601"},
        pago={"fecha": datetime(2026, 10, 3, 12, tzinfo=UTC), "forma_pago": "03", "monto": D("3696.00"), "num_operacion": "ABC123"},
        documentos=docs,
    )
    assert p["CfdiType"] == "P" and "Items" not in p and "PaymentForm" not in p
    assert p["Receiver"]["CfdiUse"] == "CP01"
    (pago,) = p["Complemento"]["Payments"]
    assert pago["Amount"] == "3696.00" and pago["OperationNumber"] == "ABC123"
    assert [d["Uuid"] for d in pago["RelatedDocuments"]] == ["uuid-1", "uuid-2"]
    assert pago["RelatedDocuments"][0]["Taxes"][1]["Name"] == "IVA RET"


def test_vencimiento_dia_5_del_mes_siguiente_con_corrimiento():
    assert fecha_vencimiento_rep(datetime(2026, 9, 20, tzinfo=UTC)) == date(2026, 10, 5)   # lunes
    assert fecha_vencimiento_rep(datetime(2026, 2, 28, tzinfo=UTC)) == date(2026, 3, 5)    # jueves
    assert fecha_vencimiento_rep(datetime(2026, 12, 15, tzinfo=UTC)) == date(2027, 1, 5)   # martes
    assert fecha_vencimiento_rep(datetime(2026, 11, 10, tzinfo=UTC)) == date(2026, 12, 7)  # 5 dic 2026 es sábado -> lunes 7
