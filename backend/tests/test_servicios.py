"""Tests de servicios y viajes — `fase-2-servicios §Definición de terminado`."""
import io

import openpyxl
from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario

API = "/api/v1"


def _auth_headers(client: TestClient, email: str, password: str = "secret123") -> dict:
    login = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _setup_catalogos(client: TestClient, headers: dict) -> dict:
    """Crea cliente (modo_acuse=referencia), unidad, operador y un lugar de ese cliente."""
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
    unidad = client.post(
        f"{API}/catalogos/unidades",
        json={
            "apodo": "Saveiro Blanca",
            "placa": "KR9417A",
            "config_vehicular": "VL",
            "peso_bruto_vehicular": 0.5,
            "perm_sct": "TPAF14",
            "num_permiso_sct": "1522ZACE14122021277602000",
        },
        headers=headers,
    ).json()
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
        json={
            "nombre_humano": "Preservativos de alimentos",
            "bienes_transp": "12164501",
            "clave_unidad": "X4G",
        },
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
        "viajes": [
            {"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
            {
                "tipo": "entrega",
                "destino_lugar_id": cat["destino"]["id"],
                "distancia_km": 70.0,
                "mercancias": [
                    {
                        "mercancia_frecuente_id": cat["mercancia"]["id"],
                        "cantidad": 10,
                        "peso_kg": 250,
                    }
                ],
            },
        ],
    }
    payload.update(overrides)
    return payload


def test_crear_servicio_con_viajes(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)

    response = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["numero"] == 1
    assert body["estado"] == "programado"
    assert body["estado_facturacion"] == "pendiente"
    assert len(body["viajes"]) == 2
    assert body["viajes"][0]["tipo"] == "recoleccion"
    assert body["viajes"][1]["mercancias"][0]["descripcion"] == "Preservativos de alimentos"
    assert body["viajes"][1]["mercancias"][0]["bienes_transp"] == "12164501"
    assert body["acciones_permitidas"] == ["editar", "duplicar", "cancelar"]


def test_servicio_sin_viajes_422(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    response = client.post(
        f"{API}/servicios", json=_servicio_payload(cat, viajes=[]), headers=headers
    )
    assert response.status_code == 422


def test_entrega_sin_destino_422(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    payload = _servicio_payload(cat, viajes=[{"tipo": "entrega"}])
    response = client.post(f"{API}/servicios", json=payload, headers=headers)
    assert response.status_code == 422


def test_timbrado_anticipado_exige_subtotal(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    payload = _servicio_payload(cat, timbrado_anticipado=True)
    response = client.post(f"{API}/servicios", json=payload, headers=headers)
    assert response.status_code == 422

    payload["subtotal"] = "1650.00"
    ok = client.post(f"{API}/servicios", json=payload, headers=headers)
    assert ok.status_code == 201, ok.text
    assert ok.json()["timbrado_anticipado"] is True


def test_timbrado_anticipado_en_cero_no_exige_subtotal(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    payload = _servicio_payload(cat, timbrado_anticipado=True, timbrado_modo="cero")
    ok = client.post(f"{API}/servicios", json=payload, headers=headers)
    assert ok.status_code == 201, ok.text
    assert ok.json()["timbrado_modo"] == "cero"

    # sin la casilla, el modo se ignora
    sin_casilla = client.post(
        f"{API}/servicios", json=_servicio_payload(cat, timbrado_modo="cero"), headers=headers
    )
    assert sin_casilla.json()["timbrado_modo"] == "precio"


def test_lista_y_conteos(
client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers)

    listado = client.get(f"{API}/servicios?vista=programados", headers=headers)
    assert listado.status_code == 200
    assert listado.json()["total"] == 1
    item = listado.json()["items"][0]
    assert item["cliente"] == "Chemital"
    assert item["ruta_resumen"] == "Planta Chemital → Tiendas Express"
    assert item["acuses_requeridos"] == 1  # solo la entrega requiere acuse (modo referencia)

    conteos = client.get(f"{API}/servicios/conteos", headers=headers).json()
    assert conteos["programados"] == 1
    assert conteos["por_facturar"] == 0


def test_editar_servicio_y_bloqueo_sin_notas_en_cancelado(
    client: TestClient, admin_user: Usuario
):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()

    editado = client.patch(
        f"{API}/servicios/{servicio['id']}", json={"notas": "urge"}, headers=headers
    )
    assert editado.status_code == 200
    assert editado.json()["notas"] == "urge"

    cancelado = client.post(
        f"{API}/servicios/{servicio['id']}/cancelar",
        json={"motivo": "cliente canceló"},
        headers=headers,
    )
    assert cancelado.status_code == 200
    assert cancelado.json()["estado"] == "cancelado"
    assert cancelado.json()["acciones_permitidas"] == []

    bloqueado = client.patch(
        f"{API}/servicios/{servicio['id']}", json={"notas": "otra nota"}, headers=headers
    )
    assert bloqueado.status_code == 409


def test_duplicar_servicio(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()

    duplicado = client.post(
        f"{API}/servicios/{servicio['id']}/duplicar",
        json={"fecha": "2026-10-10"},
        headers=headers,
    )
    assert duplicado.status_code == 201, duplicado.text
    body = duplicado.json()
    assert body["numero"] == 2
    assert body["fecha"] == "2026-10-10"
    assert len(body["viajes"]) == 2
    assert body["subtotal"] is None


def test_viajes_agregar_editar_eliminar_y_orden(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    viaje_ids = [v["id"] for v in servicio["viajes"]]

    nuevo_viaje = client.post(
        f"{API}/servicios/{servicio['id']}/viajes",
        json={"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"]},
        headers=headers,
    )
    assert nuevo_viaje.status_code == 201, nuevo_viaje.text
    assert nuevo_viaje.json()["orden"] == 3

    reordenado = client.post(
        f"{API}/servicios/{servicio['id']}/viajes/orden",
        json={"viaje_ids": [nuevo_viaje.json()["id"], *viaje_ids]},
        headers=headers,
    )
    assert reordenado.status_code == 200
    assert reordenado.json()[0]["orden"] == 1

    editar = client.patch(
        f"{API}/viajes/{viaje_ids[0]}", json={"distancia_km": 12.5}, headers=headers
    )
    assert editar.status_code == 200
    assert editar.json()["distancia_km"] == 12.5

    eliminar = client.delete(f"{API}/viajes/{nuevo_viaje.json()['id']}", headers=headers)
    assert eliminar.status_code == 204


def test_terminar_y_reabrir_viaje(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    viaje_entrega = servicio["viajes"][1]["id"]

    terminar = client.post(
        f"{API}/viajes/{viaje_entrega}/terminar",
        json={"referencia_acuse": "FOLIO-2257"},
        headers=headers,
    )
    assert terminar.status_code == 200, terminar.text
    assert terminar.json()["estado"] == "terminado"

    detalle = client.get(f"{API}/servicios/{servicio['id']}", headers=headers).json()
    assert detalle["estado"] == "en_curso"  # falta terminar la recolección

    client.post(f"{API}/viajes/{servicio['viajes'][0]['id']}/terminar", json={}, headers=headers)
    marcar = client.post(f"{API}/servicios/{servicio['id']}/marcar-terminado", headers=headers)
    assert marcar.status_code == 200
    assert marcar.json()["estado"] == "terminado"

    reabrir = client.post(f"{API}/viajes/{viaje_entrega}/reabrir", headers=headers)
    assert reabrir.status_code == 200
    assert reabrir.json()["estado"] == "pendiente"
    detalle2 = client.get(f"{API}/servicios/{servicio['id']}", headers=headers).json()
    assert detalle2["estado"] == "en_curso"


def test_acuse_referencia_completa_el_viaje(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    servicio = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    viaje_entrega = servicio["viajes"][1]["id"]

    antes = client.get(f"{API}/servicios/{servicio['id']}", headers=headers).json()
    assert antes["viajes"][1]["acuse_completo"] is False

    acuse = client.post(
        f"{API}/viajes/{viaje_entrega}/acuses", json={"referencia": "FOLIO-9"}, headers=headers
    )
    assert acuse.status_code == 201, acuse.text
    assert acuse.json()["referencia"] == "FOLIO-9"

    despues = client.get(f"{API}/servicios/{servicio['id']}", headers=headers).json()
    assert despues["viajes"][1]["acuse_completo"] is True


def test_distancia_sugerida(client: TestClient, admin_user: Usuario):
    # El par (origen_lugar_id, destino_lugar_id) solo queda en la MISMA fila de
    # `viaje` cuando el tipo es recoleccion_entrega (una entrega sola guarda su
    # origen como null: "su origen es la ubicación anterior", `02 §3.8`).
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    payload = _servicio_payload(
        cat,
        viajes=[
            {
                "tipo": "recoleccion_entrega",
                "origen_lugar_id": cat["origen"]["id"],
                "destino_lugar_id": cat["destino"]["id"],
                "distancia_km": 70.0,
            }
        ],
    )
    client.post(f"{API}/servicios", json=payload, headers=headers)

    # Sin km del cliente: 70 km marcados como no confirmados (el origen no cuenta).
    sugerida = client.get(
        f"{API}/lugares/distancia-sugerida"
        f"?origen_lugar_id={cat['origen']['id']}&destino_lugar_id={cat['destino']['id']}",
        headers=headers,
    )
    assert sugerida.status_code == 200
    assert sugerida.json() == {"distancia_km": 70.0, "fuente": "por_defecto", "confirmado": False}

    # Con el km importado del Excel de Carta Porte: ese km, confirmado (sin origen).
    baab = client.post(
        f"{API}/catalogos/lugares",
        json={
            "cliente_id": cat["cliente"]["id"],
            "nombre": "Alimentos BAAB",
            "estado": "MEX",
            "codigo_postal": "04300",
        },
        headers=headers,
    ).json()
    excel = _excel_km([["ALIMENTOS BAAB", "ABA131030NV2", "04300", "65km"], ["Sin Lugar SA", "X", "01000", 10]])
    r = client.post(
        f"{API}/catalogos/lugares/importar-km",
        files={"archivo": ("CartaPorte.xlsx", excel, "application/octet-stream")},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    hoja = r.json()["hojas"][0]
    assert hoja["actualizados"] == 1 and hoja["sin_lugar"] == ["Sin Lugar SA"]
    con_km = client.get(
        f"{API}/lugares/distancia-sugerida?destino_lugar_id={baab['id']}", headers=headers
    )
    assert con_km.json() == {"distancia_km": 65.0, "fuente": "cliente", "confirmado": True}


def test_viaje_con_cp_propio(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    payload = _servicio_payload(
        cat,
        viajes=[
            {"tipo": "recoleccion_entrega", "origen_lugar_id": cat["origen"]["id"],
             "destino_lugar_id": cat["destino"]["id"], "destino_cp": " 06600 "},
        ],
    )
    r = client.post(f"{API}/servicios", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    viaje = r.json()["viajes"][0]
    assert viaje["destino_cp"] == "06600" and viaje["origen_cp"] is None

    malo = _servicio_payload(
        cat,
        viajes=[{"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"], "destino_cp": "12"}],
    )
    assert client.post(f"{API}/servicios", json=malo, headers=headers).status_code == 422


def test_catalogo_bloquea_archivar_con_servicio_activo(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers)

    uso = client.get(
        f"{API}/catalogos/unidades/{cat['unidad']['id']}/uso", headers=headers
    ).json()
    assert uso["referencias"]["servicios"] == 1
    assert len(uso["bloqueos"]) == 1
    assert uso["bloqueos"][0]["estado"] == "programado"

    eliminar = client.delete(f"{API}/catalogos/unidades/{cat['unidad']['id']}", headers=headers)
    assert eliminar.status_code == 409

    uso_lugar = client.get(
        f"{API}/catalogos/lugares/{cat['destino']['id']}/uso", headers=headers
    ).json()
    assert uso_lugar["referencias"]["viajes"] == 1
    assert len(uso_lugar["bloqueos"]) == 1


def _excel_km(filas: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CHEMITAL"
    ws.append(["NOMBRE", "RFC", "CP", "KM"])
    for fila in filas:
        ws.append(fila)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
