"""Historial de movimientos de los admins: facturar, enviar factura y cancelar (desde 11 nov 2026)."""
import types
from datetime import date, timedelta
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import hash_password
from app.modules.auth.models import RolUsuario, Usuario
from app.modules.facturacion import facturas as facturas_service
from tests.test_facturacion import API, _auth_headers
from tests.test_facturas import _timbrar


def _historial(client, h, **params):
    r = client.get(f"{API}/historial", params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_historial_registra_facturar_enviar_y_cancelar(
    client: TestClient, session: Session, admin_user: Usuario, operador_user: Usuario, monkeypatch
):
    h = _auth_headers(client, admin_user.email)
    assert _historial(client, h)["items"] == []  # nada anterior: empieza vacío

    servicio, factura, pac = _timbrar(client, h, monkeypatch)
    # 1) facturar
    items = _historial(client, h)["items"]
    assert [i["tipo"] for i in items] == ["factura_timbrada"]
    assert items[0]["usuario"]["nombre"] == admin_user.nombre and items[0]["etiqueta"] == "Facturó"
    assert "Factura ELG7" in items[0]["descripcion"] and "Chemital" in items[0]["descripcion"] and "$1,848.00" in items[0]["descripcion"]
    assert items[0]["factura_id"] == factura["id"] and items[0]["servicio_id"] == servicio["id"]

    # 2) enviar factura
    monkeypatch.setattr(
        facturas_service, "get_settings", lambda: types.SimpleNamespace(
            resend_api_key="k", email_from="E <a@b.mx>", email_reply_to="e@x.mx", email_modo_prueba=False
        )
    )
    import resend

    monkeypatch.setattr(resend.Emails, "send", MagicMock())
    assert client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["c@x.mx"]}, headers=h).status_code == 200
    # un envío que falla NO se registra
    monkeypatch.setattr(resend.Emails, "send", MagicMock(side_effect=RuntimeError("x")))
    assert client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["c@x.mx"]}, headers=h).status_code >= 400

    # 3) cancelar la factura
    pac.cancel_cfdi.return_value = {"Status": "canceled"}
    assert client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "02"}, headers=h).status_code == 200
    # una cancelación inválida tampoco se registra
    assert client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "99"}, headers=h).status_code == 422

    # 4) cancelar un servicio (de otro admin)
    otro = Usuario(nombre="Segundo Admin", email="b@b.com", password_hash=hash_password("secret123"), rol=RolUsuario.admin)
    session.add(otro)
    session.commit()
    h2 = _auth_headers(client, "b@b.com")
    s2 = client.post(f"{API}/servicios", json=_payload_servicio_aparte(client, h), headers=h2).json()
    assert client.post(f"{API}/servicios/{s2['id']}/cancelar", json={"motivo": "cliente canceló"}, headers=h2).status_code == 200
    # cancelar uno ya cancelado falla y no se duplica
    client.post(f"{API}/servicios/{s2['id']}/cancelar", json={"motivo": "otra vez"}, headers=h2)

    todo = _historial(client, h)
    assert todo["total"] == 4
    assert [i["tipo"] for i in todo["items"]] == ["servicio_cancelado", "factura_cancelada", "factura_enviada", "factura_timbrada"]
    assert todo["items"][0]["usuario"]["nombre"] == "Segundo Admin" and "cliente canceló" in todo["items"][0]["descripcion"]
    assert "#" in todo["items"][0]["descripcion"]
    assert "c@x.mx" in todo["items"][2]["descripcion"] and "MODO PRUEBA" not in todo["items"][2]["descripcion"]

    # filtros: por admin, por tipo, por fechas (hoy sí, mañana no)
    assert [i["tipo"] for i in _historial(client, h, usuario_id=str(otro.id))["items"]] == ["servicio_cancelado"]
    assert _historial(client, h, tipo="factura_enviada")["total"] == 1
    hoy, manana = date.today(), date.today() + timedelta(days=1)
    assert _historial(client, h, desde=hoy.isoformat(), hasta=manana.isoformat())["total"] == 4
    assert _historial(client, h, desde=(manana + timedelta(days=1)).isoformat())["total"] == 0
    assert _historial(client, h, hasta=(hoy - timedelta(days=2)).isoformat())["total"] == 0
    assert client.get(f"{API}/historial", params={"desde": "ayer"}, headers=h).status_code == 422
    assert _historial(client, h, size=2, page=2)["items"][0]["tipo"] == "factura_enviada"

    f = client.get(f"{API}/historial/filtros", headers=h).json()
    assert {a["nombre"] for a in f["admins"]} == {admin_user.nombre, "Segundo Admin"}
    assert {t["value"] for t in f["tipos"]} == {"factura_timbrada", "factura_enviada", "factura_cancelada", "servicio_cancelado"}

    # solo admins
    ho = _auth_headers(client, operador_user.email)
    assert client.get(f"{API}/historial", headers=ho).status_code == 403


def _payload_servicio_aparte(client, h):
    """Servicio nuevo con el catálogo que ya creó `_timbrar` (el RFC del cliente es único)."""
    def lista(ruta):
        j = client.get(f"{API}/catalogos/{ruta}", headers=h).json()
        return j["items"] if isinstance(j, dict) else j

    lugares = lista("lugares")
    origen = next(l for l in lugares if l.get("es_origen_predeterminado"))
    destino = next(l for l in lugares if not l.get("es_origen_predeterminado"))
    return {
        "cliente_id": lista("clientes")[0]["id"], "unidad_id": lista("unidades")[0]["id"],
        "operador_id": lista("operadores")[0]["id"], "fecha": "2026-11-11",
        "viajes": [
            {"tipo": "recoleccion", "origen_lugar_id": origen["id"]},
            {"tipo": "entrega", "destino_lugar_id": destino["id"], "distancia_km": 70},
        ],
    }
