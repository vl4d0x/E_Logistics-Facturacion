"""Etiqueta "Re-escaneo" del acuse: se pide desde Facturar (o el operador termina sin escanear),
bloquea el timbrado y se quita sola al subir el escaneo nuevo."""
from fastapi.testclient import TestClient

from app.core import storage
from app.modules.auth.models import Usuario
from app.modules.servicios import router as servicios_router
from tests.test_facturacion import API, _auth_headers, _servicio_payload, _setup_catalogos
from tests.test_facturas import _R2Falso

PDF = b"%PDF-1.4 acuse de prueba"


def _servicio_escaneo(client, h):
    cat = _setup_catalogos(client, h)
    client.patch(f"{API}/catalogos/clientes/{cat['cliente']['id']}", json={"modo_acuse": "escaneo", "requiere_folio_concepto": False}, headers=h)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=h).json()
    return servicio, servicio["viajes"][1]["id"]


def _reglas(client, h, sid):
    return {c["regla"]: c for c in client.get(f"{API}/servicios/{sid}/validar", headers=h).json()["checks"]}


def test_solicitar_reescaneo_bloquea_y_subir_lo_quita(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    r2 = _R2Falso()
    monkeypatch.setattr(servicios_router, "subir_archivo", r2.subir_archivo)
    monkeypatch.setattr(storage, "url_firmada", r2.url_firmada)
    servicio, entrega = _servicio_escaneo(client, h)

    r = client.post(f"{API}/viajes/{entrega}/reescaneo", json={"motivo": "Está borroso"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["reescaneo"]["motivo"] == "Está borroso"
    assert r.json()["reescaneo"]["solicitado_por"] == admin_user.nombre

    detalle = client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()
    assert detalle["viajes"][1]["reescaneo"]["motivo"] == "Está borroso"
    lista = client.get(f"{API}/servicios?acuses_pendientes=true", headers=h).json()
    assert [s["id"] for s in lista["items"]] == [servicio["id"]] and lista["items"][0]["reescaneos"] == 1
    assert _reglas(client, h, servicio["id"])["reescaneo_pendiente"]["nivel"] == "error"
    assert client.get(f"{API}/dashboard/pendientes", headers=h).json()["acuses_faltantes"] >= 1

    # Otro admin sube el escaneo: la etiqueta se quita sola.
    r = client.post(f"{API}/viajes/{entrega}/acuses", files={"file": ("a.pdf", PDF, "application/pdf")}, headers=h)
    assert r.status_code == 201, r.text
    assert client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()["viajes"][1]["reescaneo"] is None
    assert _reglas(client, h, servicio["id"])["reescaneo_pendiente"]["nivel"] == "ok"


def test_quitar_reescaneo_y_reglas(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    servicio, entrega = _servicio_escaneo(client, h)
    recoleccion = servicio["viajes"][0]["id"]
    assert client.post(f"{API}/viajes/{recoleccion}/reescaneo", json={}, headers=h).status_code == 422
    client.post(f"{API}/viajes/{entrega}/reescaneo", json={}, headers=h)
    assert client.delete(f"{API}/viajes/{entrega}/reescaneo", headers=h).status_code == 200
    assert client.get(f"{API}/servicios?acuses_pendientes=true", headers=h).json()["items"] == []


def test_terminar_sin_escanear_deja_la_etiqueta(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    servicio, entrega = _servicio_escaneo(client, h)
    r = client.post(f"{API}/viajes/{entrega}/terminar", json={"acuse_omitido": True}, headers=h)
    assert r.status_code == 200, r.text
    viaje = client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()["viajes"][1]
    assert viaje["estado"] == "terminado"
    assert "sin escanear" in viaje["reescaneo"]["motivo"]


def test_buscador_y_filtro_de_inspeccion(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    servicio, _ = _servicio_escaneo(client, h)
    assert [s["id"] for s in client.get(f"{API}/servicios?q=chemital", headers=h).json()["items"]] == [servicio["id"]]
    assert [s["id"] for s in client.get(f"{API}/servicios?q=Tiendas", headers=h).json()["items"]] == [servicio["id"]]
    assert client.get(f"{API}/servicios?q=nadie", headers=h).json()["items"] == []
    assert client.get(f"{API}/servicios?q={servicio['numero']}", headers=h).json()["total"] == 1
    assert client.get(f"{API}/servicios?inspeccion_fallas=true", headers=h).json()["items"] == []
