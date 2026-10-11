"""Tests de `04-facturacion-cfdi §3,§5,§6` — impuestos, validación y timbrado."""
import types
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.integrations.facturama import FacturamaError
from app.modules.auth.models import Usuario
from app.modules.facturacion import service as facturacion_service

API = "/api/v1"


def _auth_headers(client: TestClient, email: str, password: str = "secret123") -> dict:
    login = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _setup_catalogos(client: TestClient, headers: dict, poliza: bool = True) -> dict:
    cliente = client.post(
        f"{API}/catalogos/clientes",
        json={
            "razon_social": "CHEMITAL DE MEXICO",
            "nombre_comercial": "Chemital",
            "rfc": "CME091007LG1",
            "cp_fiscal": "52004",
            "regimen_fiscal": "601",
            "regimen_receptor": "moral",
            "modo_acuse": "referencia",
        },
        headers=headers,
    ).json()
    unidad_payload = {
        "apodo": "Saveiro Blanca",
        "placa": "KR9417A",
        "config_vehicular": "VL",
        "peso_bruto_vehicular": 0.5,
        "perm_sct": "A4",  # distinto del default "a revisar" (TPAF14) para no ensuciar el caso "ok"
        "num_permiso_sct": "1522ZACE14122021277602000",
        "capacidad_carga_kg": 2000,
    }
    if poliza:
        unidad_payload["aseguradora_resp_civil"] = "GNP"
        unidad_payload["poliza_resp_civil"] = "POL-001"
    unidad = client.post(f"{API}/catalogos/unidades", json=unidad_payload, headers=headers).json()
    operador = client.post(
        f"{API}/catalogos/operadores",
        json={"nombre": "Enrique Zamora", "rfc": "ZACE880207MC7", "num_licencia": "LFD00065145"},
        headers=headers,
    ).json()
    origen = client.post(
        f"{API}/catalogos/lugares",
        json={
            "cliente_id": cliente["id"],
            "nombre": "Planta Chemital",
            "estado": "MEX",
            "codigo_postal": "52004",
            "es_origen_predeterminado": True,
        },
        headers=headers,
    ).json()
    destino = client.post(
        f"{API}/catalogos/lugares",
        json={"nombre": "Tiendas Express", "estado": "MEX", "codigo_postal": "52000"},
        headers=headers,
    ).json()
    mercancia = client.post(
        f"{API}/catalogos/clientes/{cliente['id']}/mercancias",
        json={"nombre_humano": "Preservativos de alimentos", "bienes_transp": "12164501", "clave_unidad": "X4G"},
        headers=headers,
    ).json()
    return {
        "cliente": cliente,
        "unidad": unidad,
        "operador": operador,
        "origen": origen,
        "destino": destino,
        "mercancia": mercancia,
    }


def _servicio_payload(cat: dict, **overrides) -> dict:
    payload = {
        "cliente_id": cat["cliente"]["id"],
        "unidad_id": cat["unidad"]["id"],
        "operador_id": cat["operador"]["id"],
        "fecha": "2026-10-03",
        "subtotal": "1650.00",
        "viajes": [
            {"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
            {
                "tipo": "entrega",
                "destino_lugar_id": cat["destino"]["id"],
                "distancia_km": 70.0,
                "mercancias": [
                    {"mercancia_frecuente_id": cat["mercancia"]["id"], "cantidad": 10, "peso_kg": 250}
                ],
            },
        ],
    }
    payload.update(overrides)
    return payload


def test_impuestos_preview_desde_subtotal(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    r = client.post(
        f"{API}/impuestos/preview",
        json={"regimen_receptor": "moral", "subtotal": "1650.00"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["iva_trasladado"] == "264.00"
    assert body["iva_retenido"] == "66.00"
    assert body["total"] == "1848.00"


def test_impuestos_preview_desde_total(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    r = client.post(
        f"{API}/impuestos/preview",
        json={"regimen_receptor": "moral", "total": "1848.00"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["subtotal"] == "1650.00"


def test_impuestos_preview_ambos_o_ninguno_422(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    ambos = client.post(
        f"{API}/impuestos/preview",
        json={"regimen_receptor": "moral", "subtotal": "100", "total": "116"},
        headers=headers,
    )
    assert ambos.status_code == 422
    ninguno = client.post(f"{API}/impuestos/preview", json={"regimen_receptor": "moral"}, headers=headers)
    assert ninguno.status_code == 422


def test_impuestos_preview_requiere_admin(client: TestClient, operador_user: Usuario):
    headers = _auth_headers(client, operador_user.email)
    r = client.post(
        f"{API}/impuestos/preview", json={"regimen_receptor": "moral", "subtotal": "100"}, headers=headers
    )
    assert r.status_code == 403


def test_validar_servicio_recien_creado_tiene_errores(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers, poliza=False)
    servicio = client.post(
        f"{API}/servicios", json=_servicio_payload(cat, subtotal=None), headers=headers
    ).json()

    r = client.get(f"{API}/servicios/{servicio['id']}/validar", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is False
    reglas_error = {c["regla"] for c in body["checks"] if c["nivel"] == "error"}
    assert "servicio_terminado" in reglas_error
    assert "subtotal_presente" in reglas_error
    assert "unidad_completa" in reglas_error  # falta póliza
    assert "acuse_por_entrega" in reglas_error  # no hay folio todavía
    assert body["preview"] is None  # sin subtotal no hay preview


def test_validar_servicio_completo_queda_ok(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers, poliza=True)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    viaje_recoleccion, viaje_entrega = servicio["viajes"][0]["id"], servicio["viajes"][1]["id"]

    client.post(
        f"{API}/viajes/{viaje_entrega}/terminar",
        json={"referencia_acuse": "FOLIO-2257"},
        headers=headers,
    )
    client.post(f"{API}/viajes/{viaje_recoleccion}/terminar", json={}, headers=headers)
    marcar = client.post(f"{API}/servicios/{servicio['id']}/marcar-terminado", headers=headers)
    assert marcar.status_code == 200

    r = client.get(f"{API}/servicios/{servicio['id']}/validar", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    errores = [c for c in body["checks"] if c["nivel"] == "error"]
    assert errores == [], errores
    assert body["ok"] is True
    assert body["preview"] == {
        "subtotal": "1650.00",
        "iva_trasladado": "264.00",
        "iva_retenido": "66.00",
        "total": "1848.00",
    }


def test_validar_requiere_admin(client: TestClient, admin_user: Usuario, operador_user: Usuario):
    headers_admin = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers_admin)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers_admin).json()

    headers_operador = _auth_headers(client, operador_user.email)
    r = client.get(f"{API}/servicios/{servicio['id']}/validar", headers=headers_operador)
    assert r.status_code == 403


def _crear_y_terminar_servicio(client: TestClient, headers: dict) -> dict:
    cat = _setup_catalogos(client, headers, poliza=True)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    viaje_recoleccion, viaje_entrega = servicio["viajes"][0]["id"], servicio["viajes"][1]["id"]
    client.post(
        f"{API}/viajes/{viaje_entrega}/terminar", json={"referencia_acuse": "FOLIO-2257"}, headers=headers
    )
    client.post(f"{API}/viajes/{viaje_recoleccion}/terminar", json={}, headers=headers)
    client.post(f"{API}/servicios/{servicio['id']}/marcar-terminado", headers=headers)
    return servicio


def test_obtener_facturacion_precargada(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, headers)

    r = client.get(f"{API}/servicios/{servicio['id']}/facturacion", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["modo"] == "normal"
    assert body["receptor"]["rfc"] == "CME091007LG1"
    assert body["receptor"]["forma_pago"] == "99"
    assert body["concepto"]["descripcion_autogenerada"] is True
    assert "FLETE UNIDAD 2 TON" in body["concepto"]["descripcion"]  # capacidad de carga, no el apodo
    assert "Saveiro" not in body["concepto"]["descripcion"]
    assert len(body["ubicaciones"]) == 2
    assert body["ubicaciones"][0]["tipo"] == "Origen"
    assert body["ubicaciones"][0]["id_ubicacion"] == "OR000001"
    assert body["ubicaciones"][1]["tipo"] == "Destino"
    assert body["ubicaciones"][1]["id_ubicacion"] == "DE000001"
    assert body["autotransporte"]["placa"] == "KR9417A"
    assert body["figura"]["rfc"] == "ZACE880207MC7"
    assert body["montos"]["total"] == "1848.00"
    assert body["validacion"]["ok"] is True
    assert body["facturama_configurado"] is False  # sin credenciales en los tests


def test_editar_facturacion_persiste_en_servicio(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, headers)

    r = client.patch(
        f"{API}/servicios/{servicio['id']}/facturacion",
        json={"subtotal": "2000.00", "descripcion_concepto": "Texto editado a mano", "uso_cfdi": "G01"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["montos"]["subtotal"] == "2000.00"
    assert body["concepto"]["descripcion"] == "Texto editado a mano"
    assert body["concepto"]["descripcion_autogenerada"] is False
    assert body["receptor"]["uso_cfdi"] == "G01"

    # "Regenerar" (mandar null) vuelve a la descripción autogenerada
    r2 = client.patch(
        f"{API}/servicios/{servicio['id']}/facturacion",
        json={"descripcion_concepto": None},
        headers=headers,
    )
    assert r2.json()["concepto"]["descripcion_autogenerada"] is True


def test_facturar_sin_credenciales_responde_facturama_no_configurado(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, headers)

    r = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "1848.00"}, headers=headers
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "facturama_no_configurado"


def test_facturar_con_errores_de_validacion_409(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers, poliza=False)
    servicio = client.post(
        f"{API}/servicios", json=_servicio_payload(cat, subtotal=None), headers=headers
    ).json()

    r = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "0.00"}, headers=headers
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_facturar_total_no_coincide_409(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, headers)

    r = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "1.00"}, headers=headers
    )
    assert r.status_code == 409
    assert r.json()["error"]["details"][0]["issue"] == "total_no_coincide"


def _settings_con_facturama_configurado():
    return types.SimpleNamespace(
        facturama_user="user",
        facturama_password="pass",
        facturama_serie="ELG",
        emisor_rfc="ZACE880207MC7",
        emisor_nombre="ENRIQUE JAVIER ZAMORA CALLEJA",
        emisor_regimen_fiscal="612",
        emisor_lugar_expedicion="52176",
    )


def test_facturar_exito_crea_factura_timbrada(client: TestClient, admin_user: Usuario, monkeypatch):
    headers = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, headers)

    mock_client = MagicMock()
    mock_client.resolve_postal_code.return_value = {"MunicipalityCode": "051", "LocationCode": ""}
    mock_client.create_cfdi.return_value = {
        "Id": "abc123",
        "Serie": "ELG",
        "Folio": 1,
        "Complement": {"TaxStamp": {"Uuid": "1d90e747-05f4-4acc-ab93-876f0f32458f"}},
    }
    monkeypatch.setattr(facturacion_service, "get_settings", _settings_con_facturama_configurado)
    monkeypatch.setattr(facturacion_service, "FacturamaClient", lambda: mock_client)

    r = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "1848.00"}, headers=headers
    )
    assert r.status_code == 200, r.text
    body = r.json()["factura"]
    assert body["uuid_fiscal"] == "1d90e747-05f4-4acc-ab93-876f0f32458f"
    assert body["estado"] == "timbrada"
    assert body["total"] == "1848.00"

    detalle = client.get(f"{API}/servicios/{servicio['id']}", headers=headers).json()
    assert detalle["estado_facturacion"] == "facturado"

    # doble clic: ya hay factura vigente -> 409, no se vuelve a timbrar
    r2 = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "1848.00"}, headers=headers
    )
    assert r2.status_code == 409


def test_facturar_error_del_pac_queda_reintentable(client: TestClient, admin_user: Usuario, monkeypatch):
    headers = _auth_headers(client, admin_user.email)
    servicio = _crear_y_terminar_servicio(client, headers)

    mock_client = MagicMock()
    mock_client.resolve_postal_code.return_value = {"MunicipalityCode": "051", "LocationCode": ""}
    mock_client.create_cfdi.side_effect = FacturamaError("No fue posible sellar el cfdi: CSD vacío")
    monkeypatch.setattr(facturacion_service, "get_settings", _settings_con_facturama_configurado)
    monkeypatch.setattr(facturacion_service, "FacturamaClient", lambda: mock_client)

    r = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "1848.00"}, headers=headers
    )
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "facturama_error"
    assert "CSD" in r.json()["error"]["message"]

    detalle = client.get(f"{API}/servicios/{servicio['id']}", headers=headers).json()
    assert detalle["estado_facturacion"] == "pendiente"  # no se marca facturado si falla

    # reintentar reutiliza la misma fila de factura "error", no crea una nueva
    mock_client.create_cfdi.side_effect = None
    mock_client.create_cfdi.return_value = {
        "Id": "xyz789",
        "Serie": "ELG",
        "Folio": 2,
        "Complement": {"TaxStamp": {"Uuid": "2e90e747-05f4-4acc-ab93-876f0f32458f"}},
    }
    r2 = client.post(
        f"{API}/servicios/{servicio['id']}/facturar", json={"total_esperado": "1848.00"}, headers=headers
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["factura"]["uuid_fiscal"] == "2e90e747-05f4-4acc-ab93-876f0f32458f"


def test_folio_por_viaje_en_el_concepto_y_editable(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers, poliza=True)
    client.patch(
        f"{API}/catalogos/clientes/{cat['cliente']['id']}",
        json={"requiere_folio_concepto": True},
        headers=headers,
    )
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    viaje_recoleccion, viaje_entrega = servicio["viajes"][0]["id"], servicio["viajes"][1]["id"]
    client.post(f"{API}/viajes/{viaje_entrega}/terminar", json={}, headers=headers)
    client.post(f"{API}/viajes/{viaje_recoleccion}/terminar", json={}, headers=headers)
    client.post(f"{API}/servicios/{servicio['id']}/marcar-terminado", headers=headers)

    # Sin folio en el destino: la validación lo pide y el concepto lo marca vacío
    sin_folio = client.get(f"{API}/servicios/{servicio['id']}/validar", headers=headers).json()
    assert any(c["regla"] == "folio_cliente_presente" for c in sin_folio["checks"] if c["nivel"] == "error")
    detalle = client.get(f"{API}/servicios/{servicio['id']}/facturacion", headers=headers).json()
    assert detalle["concepto"]["folios"] == [{"viaje_id": viaje_entrega, "destino": "Tiendas Express", "folio": None}]
    assert "DESTINO: Tiendas Express FOLIO: —" in detalle["concepto"]["descripcion"]

    # Se captura el folio del viaje y el concepto lo lleva
    r = client.put(f"{API}/viajes/{viaje_entrega}/folio", json={"folio": " 5318 "}, headers=headers)
    assert r.status_code == 200, r.text
    detalle = client.get(f"{API}/servicios/{servicio['id']}/facturacion", headers=headers).json()
    assert detalle["concepto"]["folios"][0]["folio"] == "5318"
    assert "DESTINO: Tiendas Express FOLIO: 5318" in detalle["concepto"]["descripcion"]
    ok = client.get(f"{API}/servicios/{servicio['id']}/validar", headers=headers).json()
    assert all(c["nivel"] != "error" for c in ok["checks"] if c["regla"] == "folio_cliente_presente")

    # Y se puede corregir
    client.put(f"{API}/viajes/{viaje_entrega}/folio", json={"folio": "5319"}, headers=headers)
    detalle = client.get(f"{API}/servicios/{servicio['id']}/facturacion", headers=headers).json()
    assert "FOLIO: 5319" in detalle["concepto"]["descripcion"] and "5318" not in detalle["concepto"]["descripcion"]


def test_capacidad_txt_en_toneladas():
    from app.modules.catalogos.models import Unidad

    def u(capacidad, peso):
        return Unidad(apodo="X", placa="P", config_vehicular="VL", peso_bruto_vehicular=peso,
                      perm_sct="A4", num_permiso_sct="1", capacidad_carga_kg=capacidad)

    assert facturacion_service._capacidad_txt(u(1000, 3)) == "1 TON"
    assert facturacion_service._capacidad_txt(u(500, 3)) == "0.5 TON"
    assert facturacion_service._capacidad_txt(u(1500, 3)) == "1.5 TON"
    assert facturacion_service._capacidad_txt(u(None, 0.5)) == "0.5 TON"  # sin capacidad: peso bruto
