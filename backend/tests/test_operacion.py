"""Tests de operación en campo — `fase-3 §Definición de terminado`."""
import uuid

from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario

API = "/api/v1"


def _auth_headers(client: TestClient, email: str, password: str = "secret123") -> dict:
    login = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient, admin_headers: dict, tipo_medidor="barras", num_barras=8) -> dict:
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
        headers=admin_headers,
    ).json()
    unidad_payload = {
        "apodo": "Saveiro Blanca",
        "placa": "KR9417A",
        "config_vehicular": "VL",
        "peso_bruto_vehicular": 0.5,
        "perm_sct": "TPAF14",
        "num_permiso_sct": "1522ZACE14122021277602000",
        "tipo_medidor": tipo_medidor,
    }
    if tipo_medidor == "barras":
        unidad_payload["num_barras"] = num_barras
    unidad = client.post(
        f"{API}/catalogos/unidades", json=unidad_payload, headers=admin_headers
    ).json()
    operador = client.post(
        f"{API}/catalogos/operadores",
        json={"nombre": "Enrique Zamora", "rfc": "ZACE880207MC7", "num_licencia": "LFD00065145"},
        headers=admin_headers,
    ).json()
    acceso = client.post(
        f"{API}/catalogos/operadores/{operador['id']}/acceso",
        json={"email": "enrique", "password_temporal": "temporal123"},
        headers=admin_headers,
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
        headers=admin_headers,
    ).json()
    destino = client.post(
        f"{API}/catalogos/lugares",
        json={"nombre": "Tiendas Express", "estado": "MEX", "codigo_postal": "52000"},
        headers=admin_headers,
    ).json()
    mercancia = client.post(
        f"{API}/catalogos/clientes/{cliente['id']}/mercancias",
        json={
            "nombre_humano": "Preservativos de alimentos",
            "bienes_transp": "12164501",
            "clave_unidad": "X4G",
        },
        headers=admin_headers,
    ).json()
    servicio = client.post(
        f"{API}/servicios",
        json={
            "cliente_id": cliente["id"],
            "unidad_id": unidad["id"],
            "operador_id": operador["id"],
            "fecha": "2026-10-03",
            "viajes": [
                {"tipo": "recoleccion", "origen_lugar_id": origen["id"]},
                {"tipo": "entrega", "destino_lugar_id": destino["id"]},
            ],
        },
        headers=admin_headers,
    ).json()
    return {
        "cliente": cliente,
        "unidad": unidad,
        "operador": operador,
        "mercancia": mercancia,
        "servicio": servicio,
        "operador_headers": _auth_headers(client, acceso["email"], "temporal123"),
    }


def test_operador_solo_ve_sus_servicios(client: TestClient, admin_user: Usuario):
    admin_headers = _auth_headers(client, admin_user.email)
    ctx = _setup(client, admin_headers)

    mios = client.get(f"{API}/operador/servicios", headers=ctx["operador_headers"])
    assert mios.status_code == 200
    assert len(mios.json()) == 1
    assert mios.json()[0]["numero"] == ctx["servicio"]["numero"]
    assert mios.json()[0]["mercancias_cliente"][0]["nombre_humano"] == "Preservativos de alimentos"
    assert "bienes_transp" not in mios.json()[0]["mercancias_cliente"][0]  # sin claves SAT


def test_terminar_viaje_sin_iniciar_409(client: TestClient, admin_user: Usuario):
    admin_headers = _auth_headers(client, admin_user.email)
    ctx = _setup(client, admin_headers)
    viaje_id = ctx["servicio"]["viajes"][0]["id"]

    response = client.post(
        f"{API}/operador/viajes/{viaje_id}/terminar",
        json={"client_action_id": str(uuid.uuid4()), "terminado_at": "2026-10-03T09:00:00Z"},
        headers=ctx["operador_headers"],
    )
    assert response.status_code == 409
    assert response.json()["error"]["details"][0]["issue"] == "servicio_no_iniciado"


def test_iniciar_servicio_con_barras_y_flujo_completo(client: TestClient, admin_user: Usuario):
    admin_headers = _auth_headers(client, admin_user.email)
    ctx = _setup(client, admin_headers)
    servicio_id = ctx["servicio"]["id"]
    headers = ctx["operador_headers"]

    checklist = {
        "unidad_limpia": True,
        "fumigacion_vigente": True,
        "botiquin": True,
        "casco_chaleco": True,
        "aceite_ok": True,
        "anticongelante_ok": True,
        "neumaticos_ok": False,  # un "No" no bloquea
        "extintor_ok": True,
    }
    action_id = str(uuid.uuid4())
    iniciar = client.post(
        f"{API}/operador/servicios/{servicio_id}/iniciar",
        json={
            "client_action_id": action_id,
            "realizada_at": "2026-10-03T08:00:00Z",
            "checklist": checklist,
            "lectura_medidor": {"tipo": "barras", "barras": 6, "total": 8},
            "odometro_km": 1000,
        },
        headers=headers,
    )
    assert iniciar.status_code == 200, iniciar.text
    assert iniciar.json()["estado"] == "en_curso"

    # Idempotencia: reenviar la misma acción no crea una segunda inspección.
    reenvio = client.post(
        f"{API}/operador/servicios/{servicio_id}/iniciar",
        json={
            "client_action_id": action_id,
            "realizada_at": "2026-10-03T08:00:00Z",
            "checklist": checklist,
            "lectura_medidor": {"tipo": "barras", "barras": 6, "total": 8},
        },
        headers=headers,
    )
    assert reenvio.status_code == 200

    detalle_admin = client.get(f"{API}/servicios/{servicio_id}", headers=admin_headers).json()
    assert detalle_admin["inspeccion"]["todo_ok"] is False
    assert detalle_admin["inspeccion"]["fallas"] == ["neumaticos_ok"]
    assert float(detalle_admin["inspeccion"]["nivel_combustible"]) == 0.75

    # --- terminar los dos viajes ---
    viaje1, viaje2 = ctx["servicio"]["viajes"]
    t1 = client.post(
        f"{API}/operador/viajes/{viaje1['id']}/terminar",
        json={"client_action_id": str(uuid.uuid4()), "terminado_at": "2026-10-03T09:00:00Z"},
        headers=headers,
    )
    assert t1.status_code == 200, t1.text

    t2 = client.post(
        f"{API}/operador/viajes/{viaje2['id']}/terminar",
        json={
            "client_action_id": str(uuid.uuid4()),
            "terminado_at": "2026-10-03T10:00:00Z",
            "mercancias": [
                {"mercancia_frecuente_id": ctx["mercancia"]["id"], "cantidad": 10, "peso_kg": 250}
            ],
            "referencia_acuse": "FOLIO-2257",
        },
        headers=headers,
    )
    assert t2.status_code == 200, t2.text
    # `terminar_viaje` devuelve el modelo Viaje plano (sin relaciones resueltas, igual
    # que el endpoint de admin); la mercancía snapshot se confirma vía el detalle.
    detalle_con_mercancia = client.get(f"{API}/servicios/{servicio_id}", headers=admin_headers).json()
    assert detalle_con_mercancia["viajes"][1]["mercancias"][0]["descripcion"] == "Preservativos de alimentos"

    # --- cerrar antes de terminar todos los viajes -> ya terminados, probamos el cierre ---
    carga_id = str(uuid.uuid4())
    cierre_action_id = str(uuid.uuid4())
    cerrar = client.post(
        f"{API}/operador/servicios/{servicio_id}/cerrar",
        json={
            "client_action_id": cierre_action_id,
            "cerrado_at": "2026-10-03T12:00:00Z",
            "km_por_viaje": [
                {"viaje_id": viaje1["id"], "km": 12.5},
                {"viaje_id": viaje2["id"], "km": 70.0},
            ],
            "lectura_medidor": {"tipo": "barras", "barras": 3, "total": 8},
            "odometro_km": 1090,
            "cargo_combustible": True,
            "cargas": [
                {
                    "id": carga_id,
                    "litros": "30.00",
                    "precio_litro": "24.59",
                    "importe": "737.70",
                    "cargada_at": "2026-10-03T11:30:00Z",
                }
            ],
        },
        headers=headers,
    )
    assert cerrar.status_code == 200, cerrar.text
    assert cerrar.json()["estado"] == "terminado"

    # Idempotencia del cierre: reenviar no duplica la carga ni el reporte.
    reenvio_cierre = client.post(
        f"{API}/operador/servicios/{servicio_id}/cerrar",
        json={
            "client_action_id": cierre_action_id,
            "cerrado_at": "2026-10-03T12:00:00Z",
            "km_por_viaje": [
                {"viaje_id": viaje1["id"], "km": 12.5},
                {"viaje_id": viaje2["id"], "km": 70.0},
            ],
            "lectura_medidor": {"tipo": "barras", "barras": 3, "total": 8},
            "cargo_combustible": False,
            "cargas": [],
        },
        headers=headers,
    )
    assert reenvio_cierre.status_code == 200

    detalle = client.get(f"{API}/servicios/{servicio_id}", headers=admin_headers).json()
    assert detalle["viajes"][0]["km_reportado"] == 12.5
    assert detalle["viajes"][1]["km_reportado"] == 70.0
    assert detalle["cierre"]["cargo_combustible"] is True
    assert len(detalle["cargas"]) == 1
    assert float(detalle["combustible_total"]["litros"]) == 30.0


def test_cerrar_con_viajes_pendientes_409(client: TestClient, admin_user: Usuario):
    admin_headers = _auth_headers(client, admin_user.email)
    ctx = _setup(client, admin_headers, tipo_medidor="aguja")
    servicio_id = ctx["servicio"]["id"]
    headers = ctx["operador_headers"]

    client.post(
        f"{API}/operador/servicios/{servicio_id}/iniciar",
        json={
            "client_action_id": str(uuid.uuid4()),
            "realizada_at": "2026-10-03T08:00:00Z",
            "checklist": {k: True for k in (
                "unidad_limpia", "fumigacion_vigente", "botiquin", "casco_chaleco",
                "aceite_ok", "anticongelante_ok", "neumaticos_ok", "extintor_ok",
            )},
            "lectura_medidor": {"tipo": "aguja", "octavos": 8},
        },
        headers=headers,
    )

    cerrar = client.post(
        f"{API}/operador/servicios/{servicio_id}/cerrar",
        json={
            "client_action_id": str(uuid.uuid4()),
            "cerrado_at": "2026-10-03T12:00:00Z",
            "km_por_viaje": [],
            "lectura_medidor": {"tipo": "aguja", "octavos": 4},
            "cargo_combustible": False,
            "cargas": [],
        },
        headers=headers,
    )
    assert cerrar.status_code == 409


def test_lectura_medidor_tipo_incorrecto_422(client: TestClient, admin_user: Usuario):
    admin_headers = _auth_headers(client, admin_user.email)
    ctx = _setup(client, admin_headers, tipo_medidor="aguja")
    servicio_id = ctx["servicio"]["id"]

    response = client.post(
        f"{API}/operador/servicios/{servicio_id}/iniciar",
        json={
            "client_action_id": str(uuid.uuid4()),
            "realizada_at": "2026-10-03T08:00:00Z",
            "checklist": {k: True for k in (
                "unidad_limpia", "fumigacion_vigente", "botiquin", "casco_chaleco",
                "aceite_ok", "anticongelante_ok", "neumaticos_ok", "extintor_ok",
            )},
            "lectura_medidor": {"tipo": "barras", "barras": 2, "total": 8},  # la unidad es de aguja
        },
        headers=ctx["operador_headers"],
    )
    assert response.status_code == 422


def test_servicio_ajeno_403(client: TestClient, admin_user: Usuario):
    admin_headers = _auth_headers(client, admin_user.email)
    ctx = _setup(client, admin_headers)

    otro_operador = client.post(
        f"{API}/catalogos/operadores",
        json={"nombre": "Otro", "rfc": "VAEI870904HW3", "num_licencia": "LFD00065149"},
        headers=admin_headers,
    ).json()
    otro_acceso = client.post(
        f"{API}/catalogos/operadores/{otro_operador['id']}/acceso",
        json={"email": "israel", "password_temporal": "temporal123"},
        headers=admin_headers,
    ).json()
    otro_headers = _auth_headers(client, otro_acceso["email"], "temporal123")

    response = client.post(
        f"{API}/operador/servicios/{ctx['servicio']['id']}/iniciar",
        json={
            "client_action_id": str(uuid.uuid4()),
            "realizada_at": "2026-10-03T08:00:00Z",
            "checklist": {k: True for k in (
                "unidad_limpia", "fumigacion_vigente", "botiquin", "casco_chaleco",
                "aceite_ok", "anticongelante_ok", "neumaticos_ok", "extintor_ok",
            )},
            "lectura_medidor": {"tipo": "barras", "barras": 6, "total": 8},
        },
        headers=otro_headers,
    )
    assert response.status_code == 403


def test_admin_corrige_carga(client: TestClient, admin_user: Usuario):
    admin_headers = _auth_headers(client, admin_user.email)
    ctx = _setup(client, admin_headers)
    servicio_id = ctx["servicio"]["id"]
    headers = ctx["operador_headers"]
    viaje1, viaje2 = ctx["servicio"]["viajes"]

    client.post(
        f"{API}/operador/servicios/{servicio_id}/iniciar",
        json={
            "client_action_id": str(uuid.uuid4()),
            "realizada_at": "2026-10-03T08:00:00Z",
            "checklist": {k: True for k in (
                "unidad_limpia", "fumigacion_vigente", "botiquin", "casco_chaleco",
                "aceite_ok", "anticongelante_ok", "neumaticos_ok", "extintor_ok",
            )},
            "lectura_medidor": {"tipo": "barras", "barras": 6, "total": 8},
        },
        headers=headers,
    )
    for v in (viaje1, viaje2):
        client.post(
            f"{API}/operador/viajes/{v['id']}/terminar",
            json={"client_action_id": str(uuid.uuid4()), "terminado_at": "2026-10-03T09:00:00Z"},
            headers=headers,
        )
    carga_id = str(uuid.uuid4())
    client.post(
        f"{API}/operador/servicios/{servicio_id}/cerrar",
        json={
            "client_action_id": str(uuid.uuid4()),
            "cerrado_at": "2026-10-03T12:00:00Z",
            "km_por_viaje": [{"viaje_id": v["id"], "km": 10} for v in (viaje1, viaje2)],
            "lectura_medidor": {"tipo": "barras", "barras": 3, "total": 8},
            "cargo_combustible": True,
            "cargas": [
                {
                    "id": carga_id,
                    "litros": "10.00",
                    "precio_litro": "24.00",
                    "importe": "240.00",
                    "cargada_at": "2026-10-03T11:00:00Z",
                }
            ],
        },
        headers=headers,
    )

    corregir = client.patch(
        f"{API}/cargas/{carga_id}", json={"litros": "12.00"}, headers=admin_headers
    )
    assert corregir.status_code == 200, corregir.text
    assert float(corregir.json()["litros"]) == 12.0

    eliminar = client.delete(f"{API}/cargas/{carga_id}", headers=admin_headers)
    assert eliminar.status_code == 204
