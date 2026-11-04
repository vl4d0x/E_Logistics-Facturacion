"""Fotos de evidencia opcionales del servicio: se suben, se listan, se borran y van al correo."""
import types
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core import storage
from app.modules.auth.models import Usuario
from app.modules.facturacion import facturas as facturas_service
from tests.test_facturacion import API, _auth_headers
from tests.test_facturas import _R2Falso, _timbrar

JPG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def _r2(monkeypatch):
    r2 = _R2Falso()
    r2.eliminar_archivo = lambda key: r2.objetos.pop(key, None)
    for nombre in ("subir_archivo", "leer_archivo", "url_firmada", "eliminar_archivo"):
        monkeypatch.setattr(storage, nombre, getattr(r2, nombre))
    return r2


def _subir(client, h, servicio_id, contenido, nombre="foto.jpg", mime="image/jpeg"):
    return client.post(f"{API}/servicios/{servicio_id}/fotos-evidencia", files={"file": (nombre, contenido, mime)}, headers=h)


def test_subir_listar_y_borrar(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    r2 = _r2(monkeypatch)
    servicio, _, _ = _timbrar(client, h, monkeypatch, r2)
    r = _subir(client, h, servicio["id"], JPG)
    assert r.status_code == 201, r.text
    assert r.json()["url"].startswith("https://r2.test/evidencias/")
    fotos = client.get(f"{API}/servicios/{servicio['id']}/fotos-evidencia", headers=h).json()
    assert [f["id"] for f in fotos] == [r.json()["id"]]
    assert client.delete(f"{API}/fotos-evidencia/{r.json()['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/servicios/{servicio['id']}/fotos-evidencia", headers=h).json() == []
    assert not any(k.startswith("evidencias/") for k in r2.objetos)


def test_rechaza_lo_que_no_es_foto(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    r2 = _r2(monkeypatch)
    servicio, _, _ = _timbrar(client, h, monkeypatch, r2)
    r = _subir(client, h, servicio["id"], b"%PDF-1.4 algo", "acuse.jpg", "image/jpeg")
    assert r.status_code == 422


def test_las_fotos_van_en_el_correo_de_la_factura(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    r2 = _r2(monkeypatch)
    servicio, factura, _ = _timbrar(client, h, monkeypatch, r2)
    _subir(client, h, servicio["id"], JPG)
    _subir(client, h, servicio["id"], PNG, "b.png", "image/png")
    enviado = MagicMock()
    monkeypatch.setattr(facturas_service, "get_settings", lambda: types.SimpleNamespace(
        resend_api_key="k", email_from="x", email_reply_to="e_logistics@outlook.com"))
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    r = client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["c@x.mx"]}, headers=h)
    assert r.status_code == 200, r.text
    adjuntos = enviado.call_args.args[0]["attachments"]
    nombres = [a["filename"] for a in adjuntos]
    assert nombres[-2:] == ["FACT #7-CHEMITAL_EVIDENCIA_FOTO_1.jpg", "FACT #7-CHEMITAL_EVIDENCIA_FOTO_2.png"]
    assert bytes(adjuntos[-2]["content"]) == JPG
