"""Fase 5 — pagos, aplicación, reversión, REP y cancelación (Facturama mockeado)."""
import base64
import types
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import storage
from app.modules.auth.models import Usuario
from app.modules.catalogos.models import Cliente, RegimenReceptor
from app.modules.cobranza import service as cobranza_service
from app.modules.facturacion import facturas as facturas_service
from app.modules.facturacion.models import EstadoCobro, EstadoFactura, Factura
from app.modules.servicios.models import Servicio
from tests.test_facturacion import API, _auth_headers

D = Decimal


def _cliente(session: Session, nombre="Chemital", moral=True) -> Cliente:
    c = Cliente(
        razon_social=f"{nombre} SA", nombre_comercial=nombre, rfc="CME091007LG1", cp_fiscal="52004",
        regimen_fiscal="601", regimen_receptor=RegimenReceptor.moral if moral else RegimenReceptor.fisica,
        emails_facturacion=["cobranza@x.mx"],
    )
    session.add(c)
    session.commit()
    return c


def _factura(session: Session, cliente: Cliente, numero: int, subtotal: str, dia: int) -> Factura:
    sub = D(subtotal)
    iva, ret = (sub * D("0.16")).quantize(D("0.01")), (sub * D("0.04")).quantize(D("0.01"))
    s = Servicio(
        numero=numero, cliente_id=cliente.id, unidad_id=uuid.uuid4(), operador_id=uuid.uuid4(), fecha=date(2026, 9, dia)
    )
    session.add(s)
    session.commit()
    f = Factura(
        servicio_id=s.id, estado=EstadoFactura.timbrada, uuid_fiscal=str(uuid.uuid4()), serie="ELG", folio=str(numero),
        fecha_emision=datetime(2026, 9, dia, 12, tzinfo=UTC), metodo_pago="PPD", forma_pago="99", uso_cfdi="G03",
        subtotal=sub, iva_trasladado=iva, iva_retenido=ret, total=sub + iva - ret, saldo_insoluto=sub + iva - ret,
        facturama_id=f"fac{numero}",
    )
    session.add(f)
    session.commit()
    return f


def _pago_json(cliente: Cliente, monto: str, **extra):
    return {"cliente_id": str(cliente.id), "fecha_pago": "2026-10-03T12:00:00-06:00", "monto": monto, **extra}


def _setup(client, session, admin_user):
    h = _auth_headers(client, admin_user.email)
    c = _cliente(session)
    f1, f2, f3 = (_factura(session, c, 100 + i, "1650.00", 1 + i) for i in range(3))  # total 1848.00 c/u
    return h, c, [f1, f2, f3]


def test_sugerencias_trae_servicios_de_cada_factura(client: TestClient, session: Session, admin_user: Usuario):
    h, c, (f1, f2, _f3) = _setup(client, session, admin_user)
    r = client.post(f"{API}/cobranza/sugerencias", json={"cliente_id": str(c.id), "monto": "3696.00"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_exactas"] >= 1 and body["saldo_total_cliente"] == "5544.00"
    primera = body["exactas"][0]
    assert primera["factura_ids"] == [str(f1.id), str(f2.id)]
    assert primera["facturas"][0]["servicio"]["numero"] == 100
    assert body["fifo_parcial"] is not None


def test_aplicar_actualiza_saldos_y_parcialidades(client: TestClient, session: Session, admin_user: Usuario):
    h, c, (f1, f2, _f3) = _setup(client, session, admin_user)
    body = _pago_json(c, "2848.00", aplicaciones=[
        {"factura_id": str(f1.id), "monto": "1848.00"}, {"factura_id": str(f2.id), "monto": "1000.00"},
    ])
    r = client.post(f"{API}/pagos", json=body, headers=h)
    assert r.status_code == 201, r.text
    pago = r.json()
    assert pago["estado"] == "aplicado" and pago["vence_rep"] == "2026-11-05" or pago["vence_rep"]
    assert [a["num_parcialidad"] for a in pago["aplicaciones"]] == [1, 1]
    session.refresh(f1), session.refresh(f2)
    assert (f1.saldo_insoluto, f1.estado_cobro) == (D("0.00"), EstadoCobro.pagada)
    assert (f2.saldo_insoluto, f2.estado_cobro) == (D("848.00"), EstadoCobro.parcial)


def test_aplicar_que_no_cuadra_422_y_excede_saldo_409(client: TestClient, session: Session, admin_user: Usuario):
    h, c, (f1, _f2, _f3) = _setup(client, session, admin_user)
    r = client.post(f"{API}/pagos", json=_pago_json(c, "1000.00", aplicaciones=[{"factura_id": str(f1.id), "monto": "900.00"}]), headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "aplicacion_no_cuadra"
    pago = client.post(f"{API}/pagos", json=_pago_json(c, "2000.00"), headers=h).json()
    r = client.post(f"{API}/pagos/{pago['id']}/aplicar", json={"aplicaciones": [{"factura_id": str(f1.id), "monto": "2000.00"}]}, headers=h)
    assert r.status_code == 409


def test_revertir_restaura_saldos(client: TestClient, session: Session, admin_user: Usuario):
    h, c, (f1, _f2, _f3) = _setup(client, session, admin_user)
    pago = client.post(f"{API}/pagos", json=_pago_json(c, "1848.00", aplicaciones=[{"factura_id": str(f1.id), "monto": "1848.00"}]), headers=h).json()
    r = client.post(f"{API}/pagos/{pago['id']}/revertir", headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "registrado"
    session.refresh(f1)
    assert (f1.saldo_insoluto, f1.estado_cobro) == (D("1848.00"), EstadoCobro.pendiente)


def test_cancelar_factura_con_pagos_aplicados_409(client: TestClient, session: Session, admin_user: Usuario):
    h, c, (f1, _f2, _f3) = _setup(client, session, admin_user)
    client.post(f"{API}/pagos", json=_pago_json(c, "1848.00", aplicaciones=[{"factura_id": str(f1.id), "monto": "1848.00"}]), headers=h)
    r = client.post(f"{API}/facturas/{f1.id}/cancelar", json={"motivo": "02"}, headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "factura_con_rep"


def _mock_pac(monkeypatch):
    pac = MagicMock()
    pac.__enter__.return_value = pac  # `with FacturamaClient() as client`
    pac.create_cfdi.return_value = {
        "Id": "rep1", "Serie": "REP", "Folio": 3, "Complement": {"TaxStamp": {"Uuid": "aaaaaaaa-0000-4000-8000-000000000001"}},
    }
    pac.get_file.side_effect = lambda _id, fmt: {"Content": base64.b64encode(f"{fmt}".encode()).decode()}
    monkeypatch.setattr(cobranza_service, "FacturamaClient", lambda: pac)
    monkeypatch.setattr(
        cobranza_service, "get_settings",
        lambda: types.SimpleNamespace(facturama_user="u", facturama_password="p", emisor_lugar_expedicion="52176"),
    )
    r2 = {}
    monkeypatch.setattr(storage, "subir_archivo", lambda k, c, t: r2.__setitem__(k, c))
    monkeypatch.setattr(storage, "leer_archivo", lambda k: r2[k])
    monkeypatch.setattr(storage, "url_firmada", lambda k: f"https://r2.test/{k}")
    return pac


def test_aplicar_y_generar_rep_idempotente(client: TestClient, session: Session, admin_user: Usuario, monkeypatch):
    h, c, (f1, f2, _f3) = _setup(client, session, admin_user)
    pac = _mock_pac(monkeypatch)
    body = _pago_json(c, "3696.00", emitir_rep=True, aplicaciones=[
        {"factura_id": str(f1.id), "monto": "1848.00"}, {"factura_id": str(f2.id), "monto": "1848.00"},
    ])
    r = client.post(f"{API}/pagos", json=body, headers=h)
    assert r.status_code == 201, r.text
    rep = r.json()["rep"]
    assert rep["estado"] == "timbrado" and rep["pdf_url"].startswith("https://r2.test/reps/")
    payload = pac.create_cfdi.call_args.args[0]
    assert payload["CfdiType"] == "P" and len(payload["Complemento"]["Payments"][0]["RelatedDocuments"]) == 2
    assert payload["Complemento"]["Payments"][0]["Date"] == "2026-10-03T12:00:00"  # hora local de México
    # segundo intento: no vuelve a timbrar
    again = client.post(f"{API}/pagos/{r.json()['id']}/rep", headers=h)
    assert again.status_code == 200 and again.json()["rep"]["id"] == rep["id"]
    assert pac.create_cfdi.call_count == 1
    assert client.get(f"{API}/pagos/{r.json()['id']}", headers=h).json()["estado"] == "rep_emitido"
    # con REP vigente no se puede revertir
    assert client.post(f"{API}/pagos/{r.json()['id']}/revertir", headers=h).status_code == 409


def test_error_del_pac_deja_pago_aplicado_y_rep_reintentable(client: TestClient, session: Session, admin_user: Usuario, monkeypatch):
    from app.integrations.facturama import FacturamaError

    h, c, (f1, _f2, _f3) = _setup(client, session, admin_user)
    pac = _mock_pac(monkeypatch)
    pac.create_cfdi.side_effect = FacturamaError("RFC inválido")
    r = client.post(f"{API}/pagos", json=_pago_json(c, "1848.00", emitir_rep=True, aplicaciones=[{"factura_id": str(f1.id), "monto": "1848.00"}]), headers=h)
    assert r.status_code == 502
    pago = client.get(f"{API}/pagos?cliente_id={c.id}", headers=h).json()[0]
    assert pago["estado"] == "aplicado" and pago["rep_pendiente"] is True
    pac.create_cfdi.side_effect = None
    pac.create_cfdi.return_value = {"Id": "rep2", "Serie": "REP", "Folio": 4, "Complement": {"TaxStamp": {"Uuid": "bbbbbbbb-0000-4000-8000-000000000002"}}}
    assert client.post(f"{API}/pagos/{pago['id']}/rep", headers=h).status_code == 200


def test_cancelar_rep_en_espera_y_confirmacion(client: TestClient, session: Session, admin_user: Usuario, monkeypatch):
    h, c, (f1, _f2, _f3) = _setup(client, session, admin_user)
    pac = _mock_pac(monkeypatch)
    pago = client.post(f"{API}/pagos", json=_pago_json(c, "1848.00", emitir_rep=True, aplicaciones=[{"factura_id": str(f1.id), "monto": "1848.00"}]), headers=h).json()
    rep_id = pago["rep"]["id"]
    pac.cancel_cfdi.return_value = {"Status": "pending"}
    r = client.post(f"{API}/reps/{rep_id}/cancelar", json={"motivo": "02"}, headers=h)
    assert r.json()["estado"] == "cancelacion_pendiente"
    pac.get_cfdi.return_value = {"Status": "canceled"}
    r = client.post(f"{API}/reps/{rep_id}/actualizar-estatus", headers=h)
    assert r.json()["estado"] == "cancelado"
    assert client.get(f"{API}/pagos/{pago['id']}", headers=h).json()["estado"] == "aplicado"
    # ya sin REP vigente, se puede revertir y cancelar la factura
    assert client.post(f"{API}/pagos/{pago['id']}/revertir", headers=h).status_code == 200


def test_enviar_rep_con_reply_to(client: TestClient, session: Session, admin_user: Usuario, monkeypatch):
    import resend

    h, c, (f1, _f2, _f3) = _setup(client, session, admin_user)
    _mock_pac(monkeypatch)
    pago = client.post(f"{API}/pagos", json=_pago_json(c, "1848.00", emitir_rep=True, aplicaciones=[{"factura_id": str(f1.id), "monto": "1848.00"}]), headers=h).json()
    enviado = MagicMock()
    monkeypatch.setattr(resend.Emails, "send", enviado)
    monkeypatch.setattr(
        facturas_service, "get_settings",
        lambda: types.SimpleNamespace(resend_api_key="k", email_from="E <a@b.mx>", email_reply_to="e_logistics@outlook.com"),
    )
    r = client.post(f"{API}/reps/{pago['rep']['id']}/enviar", json={}, headers=h)
    assert r.status_code == 200, r.text
    msg = enviado.call_args.args[0]
    assert msg["to"] == ["cobranza@x.mx"] and msg["reply_to"] == "e_logistics@outlook.com"
    assert [a["filename"] for a in msg["attachments"]] == ["REP3_CME091007LG1.xml", "REP3_CME091007LG1.pdf"]


def test_listados_por_cobrar_y_pagos(client: TestClient, session: Session, admin_user: Usuario):
    h, c, (f1, _f2, _f3) = _setup(client, session, admin_user)
    clientes = client.get(f"{API}/cobranza/clientes", headers=h).json()
    assert clientes[0]["saldo"] == "5544.00" and clientes[0]["facturas_abiertas"] == 3
    assert clientes[0]["saldo_vencido"] == "5544.00"  # emitidas en sept 2026, crédito de 30 días ya corrido
    facturas = client.get(f"{API}/cobranza/facturas?cliente_id={c.id}&estado_cobro=pendiente,parcial", headers=h).json()
    assert len(facturas) == 3 and facturas[0]["servicio"]["numero"] == 100
    client.post(f"{API}/pagos", json=_pago_json(c, "1848.00", aplicaciones=[{"factura_id": str(f1.id), "monto": "1848.00"}]), headers=h)
    pagos = client.get(f"{API}/pagos?rep_pendiente=true", headers=h).json()
    assert len(pagos) == 1 and pagos[0]["rep_pendiente"] is True
    pagadas = client.get(f"{API}/cobranza/facturas?estado_cobro=pagada", headers=h).json()
    assert [f["id"] for f in pagadas] == [str(f1.id)]


def test_cobranza_requiere_admin(client: TestClient, operador_user: Usuario):
    h = _auth_headers(client, operador_user.email)
    assert client.get(f"{API}/cobranza/clientes", headers=h).status_code == 403
