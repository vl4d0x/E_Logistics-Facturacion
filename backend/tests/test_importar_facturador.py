"""Facturas importadas del Facturador Electrónico: importación, lista, dashboard y REP mixto."""
import io
import uuid

import openpyxl
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.auth.models import Usuario
from tests.test_cobranza import _cliente, _factura, _mock_pac, _pago_json
from tests.test_facturacion import API, _auth_headers

ENCABEZADO = ["Ver.", "Fecha", "UUID", "Serie", "Folio", "RFC", "Razón social", "Tipo", "Estatus Comprobante",
              "Uso CFDI", "Forma Pago", "Moneda (T.C.)", "Subtotal (MXN)", "Traslado", "Retención",
              "Descuento (MXN)", "Impuestos (MXN)", "Total (MXN)", "Estatus pago (MXN)"]
U = {k: str(uuid.uuid4()) for k in ("abierta", "pagada", "parcial", "cancelada", "rechazada", "nuevo")}


def _fila(u, folio, rfc, nombre, estatus, subtotal, pagado, forma="Por definir", fecha="15/10/2026 11:02:22 AM"):
    iva, ret = round(subtotal * 0.16, 2), round(subtotal * 0.04, 2)
    total = round(subtotal + iva - ret, 2)
    return ["4.0", fecha, u, "Sin Serie", folio, rfc, nombre, "Ingreso", estatus, "G03 - Gastos en general.", forma,
            "MXN($1.00)", subtotal, f"{iva:.12f}", f"{-ret:.12f}", 0, iva - ret, total, pagado]


def _reporte(pagado_abierta=0) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte"
    ws.append(ENCABEZADO)
    ws.append(_fila(U["abierta"], "5539", "CME091007LG1", "CHEMITAL DE MEXICO", "Emitido", 2700, pagado_abierta))
    ws.append(_fila(U["pagada"], "5500", "CME091007LG1", "CHEMITAL DE MEXICO", "Emitido", 1650, 1848))
    ws.append(_fila(U["parcial"], "5413", "CME091007LG1", "CHEMITAL DE MEXICO", "Emitido", 1300, 952))
    ws.append(_fila(U["cancelada"], "5537", "CME091007LG1", "CHEMITAL DE MEXICO", "Cancelado (Directo)", 14500, 0))
    ws.append(_fila(U["rechazada"], "5100", "CME091007LG1", "CHEMITAL DE MEXICO", "Emitido (Cancelación Rechazada)", 1000, 0))
    ws.append(_fila(U["nuevo"], "4000", "STO200525R29", "SUSTAINABLE TOMORROW", "Emitido", 3000, 0, fecha="02/03/2025 09:00:00 PM"))
    ws.append(["4.0", "03/11/2026 11:07:20 AM", str(uuid.uuid4()), "Sin Serie", "1357", "CME091007LG1",
               "CHEMITAL DE MEXICO", "Pago", "Emitido", "CP01 - Pagos", "", "XXX($0.00)", 0, "0", "0", 0, 0, 0, 0])
    ws.append([None] * 11 + ["Total (Pesos MXN)", 1, "", "", 0, 1, 1, 1])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def _importar(client, h, contenido):
    r = client.post(f"{API}/facturas/importar-facturador", files={"file": ("Emision.xlsx", contenido, "application/octet-stream")}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_importar_lista_y_es_idempotente(client: TestClient, session: Session, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    chemital = _cliente(session)
    r = _importar(client, h, _reporte())
    assert r["creadas"] == 6 and r["ignoradas"] == 1  # el REP (la fila de totales no cuenta)
    assert r["canceladas"] == 1 and r["vigentes"] == 5 and r["pagadas"] == 1 and r["con_saldo"] == 4
    assert r["clientes_creados"] == ["SUSTAINABLE TOMORROW"]

    lista = client.get(f"{API}/facturas?origen=facturador", headers=h).json()
    assert len(lista) == 6 and all(f["origen"] == "facturador" and f["servicio_id"] is None for f in lista)
    abierta = next(f for f in lista if f["folio"] == "5539")
    assert abierta["serie"] is None and abierta["saldo_insoluto"] == "3024.00" and abierta["cliente_id"] == str(chemital.id)
    parcial = next(f for f in lista if f["folio"] == "5413")
    assert parcial["estado_cobro"] == "parcial" and parcial["saldo_insoluto"] == "504.00"

    # Volver a subir uno más nuevo (ya se cobró la 5539): actualiza, no duplica.
    r = _importar(client, h, _reporte(pagado_abierta=3024))
    assert r["creadas"] == 0 and r["actualizadas"] == 6
    lista = client.get(f"{API}/facturas?origen=facturador", headers=h).json()
    assert next(f for f in lista if f["folio"] == "5539")["estado_cobro"] == "pagada"


def test_lo_que_se_hace_en_el_facturador_no_se_hace_aqui(client: TestClient, session: Session, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    _cliente(session)
    _importar(client, h, _reporte())
    f = next(f for f in client.get(f"{API}/facturas?origen=facturador", headers=h).json() if f["folio"] == "5539")
    for r in (
        client.get(f"{API}/facturas/{f['id']}/descargar?formato=pdf", headers=h),
        client.post(f"{API}/facturas/{f['id']}/enviar", json={}, headers=h),
        client.post(f"{API}/facturas/{f['id']}/cancelar", json={"motivo": "02"}, headers=h),
    ):
        assert r.status_code == 409 and "Facturador" in r.json()["error"]["message"]
    assert client.get(f"{API}/facturas/{f['id']}", headers=h).json()["origen"] == "facturador"


def test_rep_con_facturas_de_ambos_sistemas(client: TestClient, session: Session, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    c = _cliente(session)
    de_la_app = _factura(session, c, 100, "1650.00", 1)  # total 1848.00
    _importar(client, h, _reporte())
    importadas = {f["folio"]: f for f in client.get(f"{API}/facturas?origen=facturador", headers=h).json()}
    pac = _mock_pac(monkeypatch)

    # Sugerencias de cobranza ya consideran las del Facturador.
    sug = client.post(f"{API}/cobranza/sugerencias", json={"cliente_id": str(c.id), "monto": "4872.00"}, headers=h).json()
    assert sug["saldo_total_cliente"] == f"{1848 + 3024 + 504 + 1120:.2f}"

    body = _pago_json(c, "5376.00", emitir_rep=True, aplicaciones=[
        {"factura_id": str(de_la_app.id), "monto": "1848.00"},
        {"factura_id": importadas["5539"]["id"], "monto": "3024.00"},
        {"factura_id": importadas["5413"]["id"], "monto": "504.00"},
    ])
    r = client.post(f"{API}/pagos", json=body, headers=h)
    assert r.status_code == 201, r.text
    docs = {d.get("Folio"): d for d in pac.create_cfdi.call_args.args[0]["Complemento"]["Payments"][0]["RelatedDocuments"]}
    assert docs["5539"]["Uuid"] == U["abierta"] and "Serie" not in docs["5539"] and docs["5539"]["PartialityNumber"] == "1"
    assert docs["5539"]["ImpSaldoInsoluto"] == "0.00"
    # La 5413 ya llevaba un cobro en el Facturador: esta es la parcialidad 2 y sus impuestos son proporcionales.
    assert docs["5413"]["PartialityNumber"] == "2" and docs["5413"]["PreviousBalanceAmount"] == "504.00"
    iva = next(t for t in docs["5413"]["Taxes"] if t["IsRetention"] == "false")
    assert iva["Base"] == "450.00" and iva["Total"] == "72.00"
    lista = {f["folio"]: f for f in client.get(f"{API}/facturas?origen=facturador", headers=h).json()}
    assert lista["5539"]["estado_cobro"] == "pagada" and lista["5413"]["estado_cobro"] == "pagada"

    # Re-importar no "revive" el saldo cobrado en la app.
    _importar(client, h, _reporte())
    lista = {f["folio"]: f for f in client.get(f"{API}/facturas?origen=facturador", headers=h).json()}
    assert lista["5539"]["saldo_insoluto"] == "0.00"


def test_rep_a_cliente_creado_por_la_importacion_pide_datos_fiscales(client: TestClient, session: Session, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _importar(client, h, _reporte())
    f = next(f for f in client.get(f"{API}/facturas?origen=facturador", headers=h).json() if f["folio"] == "4000")
    _mock_pac(monkeypatch)
    r = client.post(
        f"{API}/pagos",
        json={"cliente_id": f["cliente_id"], "fecha_pago": "2026-10-03T12:00:00-06:00", "monto": "3360.00",
              "emitir_rep": True, "aplicaciones": [{"factura_id": f["id"], "monto": "3360.00"}]},
        headers=h,
    )
    # El pago se aplica, pero el REP avisa que faltan CP y régimen fiscal del cliente.
    assert r.status_code == 201, r.text
    assert "Completa el código postal" in (r.json().get("rep_error") or "")


def test_dashboard_cuenta_lo_importado(client: TestClient, session: Session, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    _cliente(session)
    _importar(client, h, _reporte())
    ing = client.get(f"{API}/dashboard/ingresos?anio=2026&mes=10", headers=h).json()["periodo"]
    # Octubre 2026: vigentes 5539 (3024), 5500 (1848, cobrada), 5413 (1456, cobrado 952), 5100 (1120)
    assert ing["facturado"] == f"{3024 + 1848 + 1456 + 1120:.2f}"
    assert ing["cobrado"] == f"{1848 + 952:.2f}"
    pc = client.get(f"{API}/dashboard/por-cobrar", headers=h).json()
    assert {i["cliente"]["nombre_comercial"] for i in pc["items"]} == {"Chemital", "SUSTAINABLE TOMORROW"}
