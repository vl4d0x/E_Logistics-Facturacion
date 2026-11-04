"""H4.7-H4.10 — archivos, lista, descarga, correo y cancelación de facturas timbradas."""
import base64
import uuid
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
    assert "cc" not in msg  # sin EMAIL_COPIA configurado
    assert [a["filename"] for a in msg["attachments"]] == ["ELG7_CME091007LG1.xml", "ELG7_CME091007LG1.pdf"]
    assert r.json()["enviado_at"] is not None and r.json()["envio_destinatarios"] == ["cliente@x.mx"]


def test_modo_prueba_redirige_el_correo_al_buzon_de_prueba(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    enviado = MagicMock()
    monkeypatch.setattr(
        facturas_service, "get_settings", lambda: types.SimpleNamespace(
            resend_api_key="k", email_from="Elogistics <a@b.mx>", email_reply_to="e_logistics@outlook.com",
            email_modo_prueba=True, email_prueba_destino="prueba@elogistics.mx",
        )
    )
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    r = client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["cliente@x.mx"]}, headers=h)
    assert r.status_code == 200, r.text
    msg = enviado.call_args.args[0]
    assert msg["to"] == ["prueba@elogistics.mx"]  # nunca al cliente
    assert msg["subject"].startswith("[PRUEBA] Factura ELG7")
    assert "cliente@x.mx" in msg["html"] and "MODO PRUEBA" in msg["html"]
    assert r.json()["envio_destinatarios"] == ["prueba@elogistics.mx"]
    assert r.json()["enviado_at"] is None  # el cliente no la recibió: sigue "sin enviar"

    # sin EMAIL_PRUEBA_DESTINO cae al buzón de respuestas de Elogistics
    monkeypatch.setattr(
        facturas_service, "get_settings", lambda: types.SimpleNamespace(
            resend_api_key="k", email_from="x", email_reply_to="e_logistics@outlook.com",
            email_modo_prueba=True, email_prueba_destino=None,
        )
    )
    client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["cliente@x.mx"]}, headers=h)
    assert enviado.call_args.args[0]["to"] == ["e_logistics@outlook.com"]


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


def _cancelacion_en_espera(client, h, monkeypatch):
    servicio, factura, pac = _timbrar(client, h, monkeypatch)
    pac.cancel_cfdi.return_value = {"Status": "pending"}
    client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "02"}, headers=h)
    return servicio, factura, pac


def test_actualizar_estatus_aceptada_cancela_y_libera(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    servicio, factura, pac = _cancelacion_en_espera(client, h, monkeypatch)
    pac.get_cfdi.return_value = {"Status": "canceled"}
    r = client.post(f"{API}/facturas/{factura['id']}/actualizar-estatus", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "cancelada" and r.json()["cancelada_at"] is not None
    assert client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()["estado_facturacion"] == "pendiente"


def test_actualizar_estatus_rechazada_vuelve_a_timbrada(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    servicio, factura, pac = _cancelacion_en_espera(client, h, monkeypatch)
    pac.get_cfdi.return_value = {"Status": "active"}
    r = client.post(f"{API}/facturas/{factura['id']}/actualizar-estatus", headers=h)
    assert r.json()["estado"] == "timbrada" and r.json()["cancelacion_solicitada_at"] is None
    assert client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()["estado_facturacion"] == "facturado"


def test_actualizar_estatus_sigue_pendiente_y_throttle(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, pac = _cancelacion_en_espera(client, h, monkeypatch)
    pac.get_cfdi.return_value = {"Status": "pending"}
    assert client.post(f"{API}/facturas/{factura['id']}/actualizar-estatus", headers=h).json()["estado"] == "cancelacion_pendiente"
    # segunda consulta dentro de 5 min -> 409
    assert client.post(f"{API}/facturas/{factura['id']}/actualizar-estatus", headers=h).status_code == 409


def test_actualizar_estatus_solo_con_cancelacion_en_espera(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    assert client.post(f"{API}/facturas/{factura['id']}/actualizar-estatus", headers=h).status_code == 409


def test_cancelar_guarda_acuse_en_r2(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    r2 = _R2Falso()
    _, factura, pac = _timbrar(client, h, monkeypatch, r2)
    pac.cancel_cfdi.return_value = {"Status": "canceled", "AcuseXmlBase64": base64.b64encode(b"<acuse/>").decode()}
    client.post(f"{API}/facturas/{factura['id']}/cancelar", json={"motivo": "02"}, headers=h)
    assert r2.objetos[f"facturas/{factura['id']}_acuse_cancelacion.xml"] == b"<acuse/>"


def _pdf_de_paginas(n: int) -> bytes:
    import io

    from pypdf import PdfWriter

    w = PdfWriter()
    for _ in range(n):
        w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_correo_une_los_acuses_pdf_en_un_solo_archivo_de_evidencia(client: TestClient, admin_user: Usuario, monkeypatch):
    import io

    from pypdf import PdfReader

    from app.modules.servicios import router as servicios_router

    h = _auth_headers(client, admin_user.email)
    r2 = _R2Falso()
    servicio, factura, _ = _timbrar(client, h, monkeypatch, r2)
    monkeypatch.setattr(servicios_router, "subir_archivo", r2.subir_archivo)
    detalle = client.get(f"{API}/servicios/{servicio['id']}", headers=h).json()
    client.patch(f"{API}/catalogos/clientes/{detalle['cliente']['id']}", json={"modo_acuse": "escaneo"}, headers=h)
    for viaje, paginas in zip(detalle["viajes"], (1, 2)):
        r = client.post(
            f"{API}/viajes/{viaje['id']}/acuses",
            files={"file": ("acuse.pdf", _pdf_de_paginas(paginas), "application/pdf")},
            headers=h,
        )
        assert r.status_code == 201, r.text

    enviado = MagicMock()
    monkeypatch.setattr(
        facturas_service, "get_settings", lambda: types.SimpleNamespace(
            resend_api_key="k", email_from="x", email_reply_to="r@x.mx", email_modo_prueba=False
        )
    )
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    r = client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["c@x.mx"]}, headers=h)
    assert r.status_code == 200, r.text
    adjuntos = enviado.call_args.args[0]["attachments"]
    assert [a["filename"] for a in adjuntos] == [
        "ELG7_CME091007LG1.xml",
        "ELG7_CME091007LG1.pdf",
        "FACT #7-CHEMITAL_EVIDENCIA.pdf",
    ]
    evidencia = PdfReader(io.BytesIO(bytes(adjuntos[2]["content"])))
    assert len(evidencia.pages) == 3  # 1 + 2 páginas, unidas en un solo PDF


def _settings_correo(**extra):
    base = dict(
        resend_api_key="k", email_from="Elogistics <a@b.mx>", email_reply_to="e_logistics@outlook.com",
        email_modo_prueba=False, email_prueba_destino=None, email_copia="e_logistics@outlook.com",
    )
    return lambda: types.SimpleNamespace(**{**base, **extra})


def test_todo_correo_lleva_copia_a_elogistics(client: TestClient, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    enviado = MagicMock()
    monkeypatch.setattr(facturas_service, "get_settings", _settings_correo())
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["cliente@x.mx"]}, headers=h)
    assert enviado.call_args.args[0]["cc"] == ["e_logistics@outlook.com"]
    # si el destinatario ya es ese buzón, no se duplica
    client.post(f"{API}/facturas/{factura['id']}/enviar", json={"to": ["E_Logistics@outlook.com"]}, headers=h)
    assert "cc" not in enviado.call_args.args[0]


def _con_correos_del_cliente(session, factura_id, correos):
    from app.modules.catalogos.models import Cliente
    from app.modules.facturacion.models import Factura

    f = session.get(Factura, uuid.UUID(factura_id))
    c = session.get(Cliente, f.cliente_id)
    c.emails_facturacion = correos
    session.add(c)
    session.commit()


def test_enviar_todas_manda_cada_factura_una_sola_vez(client: TestClient, session, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    _con_correos_del_cliente(session, factura["id"], ["pagos@cliente.mx", "cxp@cliente.mx"])
    enviado = MagicMock()
    monkeypatch.setattr(facturas_service, "get_settings", _settings_correo())
    monkeypatch.setattr(facturas_service, "ENVIO_EN_BLOQUE_DESDE", facturas_service.datetime(2000, 1, 1, tzinfo=facturas_service.MX))
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)

    pendiente = client.get(f"{API}/facturas/envio-pendiente", headers=h).json()
    assert pendiente["modo_prueba"] is False and pendiente["copia"] == "e_logistics@outlook.com"
    assert [f["id"] for f in pendiente["facturas"]] == [factura["id"]]
    assert pendiente["facturas"][0]["destinatarios"] == ["pagos@cliente.mx", "cxp@cliente.mx"]

    r = client.post(f"{API}/facturas/enviar-pendientes", json={"ids": [factura["id"]]}, headers=h)
    assert r.status_code == 200, r.text
    assert [e["id"] for e in r.json()["enviadas"]] == [factura["id"]]
    msg = enviado.call_args.args[0]
    assert msg["to"] == ["pagos@cliente.mx", "cxp@cliente.mx"] and msg["cc"] == ["e_logistics@outlook.com"]

    # segundo clic: no se vuelve a mandar
    r = client.post(f"{API}/facturas/enviar-pendientes", json={"ids": [factura["id"], factura["id"]]}, headers=h)
    assert r.json()["enviadas"] == [] and r.json()["omitidas"][0]["motivo"] == "Ya se había enviado"
    assert enviado.call_count == 1
    assert client.get(f"{API}/facturas/envio-pendiente", headers=h).json()["facturas"] == []


def test_enviar_todas_en_modo_prueba_no_marca_enviada(client: TestClient, session, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    _con_correos_del_cliente(session, factura["id"], ["pagos@cliente.mx"])
    enviado = MagicMock()
    monkeypatch.setattr(facturas_service, "get_settings", _settings_correo(email_modo_prueba=True))
    monkeypatch.setattr(facturas_service, "ENVIO_EN_BLOQUE_DESDE", facturas_service.datetime(2000, 1, 1, tzinfo=facturas_service.MX))
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    pendiente = client.get(f"{API}/facturas/envio-pendiente", headers=h).json()
    assert pendiente["modo_prueba"] is True and pendiente["destino_prueba"] == "e_logistics@outlook.com"
    r = client.post(f"{API}/facturas/enviar-pendientes", json={"ids": [factura["id"]]}, headers=h)
    assert len(r.json()["enviadas"]) == 1
    assert enviado.call_args.args[0]["to"] == ["e_logistics@outlook.com"]
    # sigue pendiente para cuando se envíe de verdad
    assert len(client.get(f"{API}/facturas/envio-pendiente", headers=h).json()["facturas"]) == 1


def test_enviar_todas_omite_sin_correo_y_anteriores_al_corte(client: TestClient, session, admin_user: Usuario, monkeypatch):
    h = _auth_headers(client, admin_user.email)
    _, factura, _ = _timbrar(client, h, monkeypatch)
    _con_correos_del_cliente(session, factura["id"], [])
    enviado = MagicMock()
    monkeypatch.setattr(facturas_service, "get_settings", _settings_correo())
    import resend

    monkeypatch.setattr(resend.Emails, "send", enviado)
    monkeypatch.setattr(facturas_service, "ENVIO_EN_BLOQUE_DESDE", facturas_service.datetime(2000, 1, 1, tzinfo=facturas_service.MX))
    fila = client.get(f"{API}/facturas/envio-pendiente", headers=h).json()["facturas"][0]
    assert fila["motivo_no_enviable"] == "El cliente no tiene correos de facturación"
    r = client.post(f"{API}/facturas/enviar-pendientes", json={"ids": [factura["id"]]}, headers=h).json()
    assert r["enviadas"] == [] and len(r["omitidas"]) == 1
    enviado.assert_not_called()

    # timbradas antes del corte (las del sandbox en producción) ni aparecen
    monkeypatch.setattr(facturas_service, "ENVIO_EN_BLOQUE_DESDE", facturas_service.datetime(2999, 1, 1, tzinfo=facturas_service.MX))
    assert client.get(f"{API}/facturas/envio-pendiente", headers=h).json()["facturas"] == []
