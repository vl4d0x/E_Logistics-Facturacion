"""Desglose de precio por destino (pantalla Facturar) y texto del correo por cliente."""
import types
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario
from app.modules.facturacion import facturas as facturas_service
from app.modules.facturacion.facturas import (
    PLANTILLA_CORREO_DEFAULT,
    tabla_desglose_html,
    texto_correo,
)
from tests.test_facturacion import API, _auth_headers, _crear_y_terminar_servicio
from tests.test_facturas import _timbrar


def _regla(detalle: dict, regla: str) -> dict:
    return next(c for c in detalle["validacion"]["checks"] if c["regla"] == regla)


def test_texto_correo_usa_la_plantilla_o_la_general():
    valores = {"folio": "120", "dia": "11", "mes": "octubre", "anio": "2026"}
    assert texto_correo(None, valores) == "Buen día, envío la factura #120, correspondiente al día 11 de octubre del 2026."
    assert PLANTILLA_CORREO_DEFAULT.startswith("Buen día")
    assert texto_correo("{operador} -> {desconocido}", {"operador": "GERMAN"}) == "GERMAN -> {desconocido}"


def test_tabla_desglose_escapa_y_suma():
    html = tabla_desglose_html([("A & B", Decimal(1000)), ("C", Decimal("650.5"))], Decimal("1650.50"))
    assert "A &amp; B" in html and "$1,000.00" in html and "$650.50" in html and "$1,650.50" in html


def test_un_solo_destino_se_lleva_todo_el_subtotal(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, h)
    detalle = client.get(f"{API}/servicios/{servicio['id']}/facturacion", headers=h).json()
    assert detalle["desglose_precio"] == [
        {"viaje_id": servicio["viajes"][1]["id"], "destino": "Tiendas Express", "monto": "1650.00", "capturado": False}
    ]
    assert _regla(detalle, "desglose_precio")["nivel"] == "ok"


def test_varios_destinos_deben_sumar_el_subtotal(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, h)
    destino2 = client.post(
        f"{API}/catalogos/lugares", json={"nombre": "Bodega Norte", "estado": "MEX", "codigo_postal": "52000"}, headers=h
    ).json()
    r = client.post(
        f"{API}/servicios/{servicio['id']}/viajes",
        json={"tipo": "entrega", "destino_lugar_id": destino2["id"], "distancia_km": 10},
        headers=h,
    )
    assert r.status_code in (200, 201), r.text
    url = f"{API}/servicios/{servicio['id']}/facturacion"
    detalle = client.get(url, headers=h).json()
    ids = [d["viaje_id"] for d in detalle["desglose_precio"]]
    assert len(ids) == 2
    assert _regla(detalle, "desglose_precio")["nivel"] == "warning"  # sin capturar: correo sin tabla

    put = f"{API}/servicios/{servicio['id']}/desglose-precio"
    detalle = client.put(put, json=[{"viaje_id": ids[0], "monto": "1000"}], headers=h).json()
    assert _regla(detalle, "desglose_precio")["nivel"] == "error"  # falta un destino

    detalle = client.put(put, json=[{"viaje_id": ids[1], "monto": "600"}], headers=h).json()
    regla = _regla(detalle, "desglose_precio")
    assert regla["nivel"] == "error" and "$1,600.00" in regla["mensaje"]

    detalle = client.put(put, json=[{"viaje_id": ids[1], "monto": "650"}], headers=h).json()
    assert _regla(detalle, "desglose_precio")["nivel"] == "ok"
    assert [d["monto"] for d in detalle["desglose_precio"]] == ["1000.00", "650.00"]

    # Un viaje que no es destino del servicio no se acepta.
    r = client.put(put, json=[{"viaje_id": servicio["viajes"][0]["id"], "monto": "1"}], headers=h)
    assert r.status_code == 422


def test_correo_con_plantilla_del_cliente_y_tabla_del_desglose(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    servicio, factura, _ = _timbrar(client, h, monkeypatch)
    detalle = client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()
    viaje_destino = servicio["viajes"][1]["id"]

    # Ya timbrada: el desglose se puede corregir, pero tiene que cuadrar con el subtotal.
    put = f"{API}/servicios/{servicio['id']}/desglose-precio"
    assert client.put(put, json=[{"viaje_id": viaje_destino, "monto": "100"}], headers=h).status_code == 422
    assert client.put(put, json=[{"viaje_id": viaje_destino, "monto": "1650"}], headers=h).status_code == 200

    client.patch(
        f"{API}/catalogos/clientes/{detalle['cliente']['id']}",
        json={"plantilla_correo": "Hola\n{operador} {unidad} {origen} -> {destinos}\nFactura #{folio} del {dia} de {mes} del {anio}"},
        headers=h,
    )
    enviado = MagicMock()
    monkeypatch.setattr(
        facturas_service,
        "get_settings",
        lambda: types.SimpleNamespace(resend_api_key="k", email_from="x", email_reply_to="r@x.mx", email_modo_prueba=False),
    )
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    r = client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["c@x.mx"]}, headers=h)
    assert r.status_code == 200, r.text
    html = enviado.call_args.args[0]["html"]
    operador, unidad = detalle["operador"]["nombre"].upper(), detalle["unidad"]["apodo"].upper()
    assert f"Hola<br>{operador} {unidad}" in html
    assert "-&gt; TIENDAS EXPRESS" in html
    assert "Factura #7 del 3 de octubre del 2026" in html
    assert "<table" in html and "Tiendas Express" in html and "$1,650.00" in html
