"""H4.7-H4.10 — archivos, lista, descarga, correo y cancelación de facturas timbradas."""
import base64
import types
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core import storage
from app.modules.auth.models import Usuario
from app.modules.facturacion import facturas as facturas_service
from app.modules.facturacion import service as facturacion_service
from tests.test_facturacion import (
    API,
    _auth_headers,
    _crear_y_terminar_servicio,
    _settings_con_facturama_configurado,
)


class _R2Falso:
    """Reemplaza `app.core.storage` en memoria."""

    def __init__(self):
        self.objetos: dict[str, bytes] = {}

    def subir_archivo(self, key, contenido, content_type):
        self.objetos[key] = contenido

    def leer_archivo(self, key):
        return self.objetos[key]

    def url_firmada(self, key):
        return f"https://r2.test/{key}"


def _timbrar(client, headers, monkeypatch, r2=None):
    servicio = _crear_y_terminar_servicio(client, headers)
    pac = MagicMock()
    pac.resolve_postal_code.return_value = {"MunicipalityCode": "051", "LocationCode": ""}
    pac.create_cfdi.return_value = {
        "Id": "abc123",
        "Serie": "ELG",
        "Folio": 7,
        "Complement": {"TaxStamp": {"Uuid": "1d90e747-05f4-4acc-ab93-876f0f32458f"}},
    }
    pac.get_file.side_effect = lambda _id, fmt: {"Content": base64.b64encode(f"{fmt}-contenido".encode()).decode()}
    monkeypatch.setattr(facturacion_service, "get_settings", _settings_con_facturama_configurado)
    monkeypatch.setattr(facturacion_service, "FacturamaClient", lambda: pac)
    monkeypatch.setattr(facturas_service, "FacturamaClient", lambda: pac)
    if r2:
        for nombre in ("subir_archivo", "leer_archivo", "url_firmada"):
            monkeypatch.setattr(storage, nombre, getattr(r2, nombre))
    r = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "1848.00"}, headers=headers
    )
    assert r.status_code == 200, r.text
    return servicio, r.json()["factura"], pac


def test_timbrar_guarda_archivos_en_r2(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    r2 = _R2Falso()
    _, factura, _ = _timbrar(client, h, monkeypatch, r2)
    assert factura["pdf_url"].startswith("https://r2.test/facturas/")
    assert len(r2.objetos) == 2
    detalle = client.get(f"{API}/facturas/{factura['id']}", headers=h).json()
    assert detalle["archivos_guardados"] is True


def test_fallo_de_r2_deja_factura_timbrada_y_se_reintenta(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)

    def roto(*a, **k):
        raise RuntimeError("R2 caído")

    monkeypatch.setattr(storage, "subir_archivo", roto)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    assert factura["estado"] == "timbrada" and factura["pdf_url"] is None
    assert client.get(f"{API}/facturas/{factura['id']}", headers=h).json()["archivos_guardados"] is False

    r2 = _R2Falso()
    monkeypatch.setattr(storage, "subir_archivo", r2.subir_archivo)
    r = client.post(f"{API}/facturas/{factura['id']}/reintentar-archivos", headers=h)
    assert r.json() == {"archivos_guardados": True}


def test_descargar_con_nombre_serie_folio_rfc(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)  # sin R2: cae a Facturama
    r = client.get(f"{API}/facturas/{factura['id']}/descargar?formato=pdf", headers=h)
    assert r.status_code == 200 and r.content == b"pdf-contenido"
    assert 'filename="ELG7_CME091007LG1.pdf"' in r.headers["content-disposition"]
    assert client.get(f"{API}/facturas/{factura['id']}/descargar?formato=exe", headers=h).status_code == 422


def test_lista_con_filtros(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    servicio, factura, _ = _timbrar(client, h, monkeypatch)
    filas = client.get(f"{API}/facturas", headers=h).json()
    assert [f["id"] for f in filas] == [factura["id"]]
    assert filas[0]["servicio_numero"] == servicio["numero"]
    assert client.get(f"{API}/facturas?estado=cancelada", headers=h).json() == []
    assert client.get(f"{API}/facturas?mes=1999-01", headers=h).json() == []
    assert client.get(f"{API}/facturas?mes=basura", headers=h).status_code == 422


def test_cancelar_inmediata_libera_el_servicio(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    servicio, factura, pac = _timbrar(client, h, monkeypatch)
    pac.cancel_cfdi.return_value = {"Status": "canceled"}
    r = client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "02"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "cancelada"
    pac.cancel_cfdi.assert_called_once_with("abc123", "02")
    s = client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()
    assert s["estado_facturacion"] == "pendiente"


def test_cancelar_en_espera_mantiene_bloqueado(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    servicio, factura, pac = _timbrar(client, h, monkeypatch)
    pac.cancel_cfdi.return_value = {"Status": "pending"}
    r = client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "02"}, headers=h)
    assert r.json()["estado"] == "cancelacion_pendiente"
    assert r.json()["cancelacion_solicitada_at"] is not None
    s = client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()
    assert s["estado_facturacion"] == "facturado"
    # ya no está "timbrada": no se puede volver a cancelar
    assert client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "02"}, headers=h).status_code == 409


def test_cancelar_motivo_invalido(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    r = client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "01"}, headers=h)
    assert r.status_code == 422


def test_enviar_correo_con_adjuntos(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    enviado = MagicMock()
    monkeypatch.setattr(
        facturas_service, "get_settings", lambda: types.SimpleNamespace(
            resend_api_key="k", email_from="Elogistics <a@b.mx>", email_reply_to="e_logistics@outlook.com"
        )
    )
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    r = client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["cliente@x.mx"]}, headers=h)
    assert r.status_code == 200, r.text
    msg = enviado.call_args.args[0]
    assert msg["to"] == ["cliente@x.mx"]
    assert msg["reply_to"] == "e_logistics@outlook.com"
    assert msg["subject"].startswith("Factura ELG7 · Servicio #")
    assert [a["filename"] for a in msg["attachments"]] == ["ELG7_CME091007LG1.xml", "ELG7_CME091007LG1.pdf"]
    assert r.json()["enviado_at"] is not None and r.json()["envio_destinatarios"] == ["cliente@x.mx"]


def test_enviar_sin_destinatarios_422_y_error_de_resend_se_registra(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    monkeypatch.setattr(
        facturas_service, "get_settings", lambda: types.SimpleNamespace(resend_api_key="k", email_from="x", email_reply_to="r@x.mx")
    )
    assert client.post(f"{API}/facturas/{factura['id']}/enviar", json={}, headers=h).status_code == 422
    import resend

    monkeypatch.setattr(resend.Emails, "send", MagicMock(side_effect=RuntimeError("dominio no verificado")))
    r = client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["a@b.mx"]}, headers=h)
    assert r.status_code == 502
    assert "dominio no verificado" in client.get(f"{API}/facturas/{factura['id']}", headers=h).json()["envio_error"]
