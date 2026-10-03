"""Tests de `04-facturacion-cfdi §3,§5` — impuestos y validación pre-timbrado."""
from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario

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
