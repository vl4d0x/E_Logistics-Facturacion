"""Tests de servicios y viajes — `fase-2-servicios §Definición de terminado`."""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.auth.models import Usuario
from app.modules.facturacion.models import EstadoFactura, Factura

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
    sin_mercancias = [
        {"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
        {"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"]},
    ]
    payload = _servicio_payload(
        cat, timbrado_anticipado=True, timbrado_modo="cero", viajes=sin_mercancias
    )
    ok =client.post(f"{API}/servicios", json=payload, headers=headers)
    assert ok.status_code == 201, ok.text
    assert ok.json()["timbrado_modo"] == "cero"
    # sin mercancías capturadas, se agrega 1 kg de "Preservativos de alimentos" al primer destino
    mercancias = [m for v in ok.json()["viajes"] for m in v["mercancias"]]
    assert [(m["descripcion"], m["peso_kg"]) for m in mercancias] == [("Preservativos de alimentos", 1.0)]

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
    # Con km capturado en el catálogo de Lugares: ese km, confirmado (sin importar el origen).
    editado = client.patch(
        f"{API}/catalogos/lugares/{baab['id']}", json={"distancia_km": 65}, headers=headers
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["distancia_km"] == 65.0
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


def test_solo_un_origen_por_servicio(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    dos_origenes = _servicio_payload(
        cat,
        viajes=[
            {"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
            {"tipo": "recoleccion_entrega", "origen_lugar_id": cat["origen"]["id"],
             "destino_lugar_id": cat["destino"]["id"]},
        ],
    )
    assert client.post(f"{API}/servicios", json=dos_origenes, headers=headers).status_code == 422

    # Un origen y varias entregas sí se permite
    ok = client.post(
        f"{API}/servicios",
        json=_servicio_payload(
            cat,
            viajes=[
                {"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
                {"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"]},
                {"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"]},
            ],
        ),
        headers=headers,
    )
    assert ok.status_code == 201, ok.text
    sid = ok.json()["id"]

    # Agregar otro origen o convertir una entrega en recolección-entrega: 422
    extra = client.post(
        f"{API}/servicios/{sid}/viajes",
        json={"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
        headers=headers,
    )
    assert extra.status_code == 422
    entrega = ok.json()["viajes"][1]["id"]
    assert client.patch(f"{API}/viajes/{entrega}", json={"tipo": "recoleccion_entrega"}, headers=headers).status_code == 422


def test_origen_agregado_despues_queda_primero(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    creado = client.post(
        f"{API}/servicios",
        json=_servicio_payload(cat, viajes=[{"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"]}]),
        headers=headers,
    ).json()
    r = client.post(
        f"{API}/servicios/{creado['id']}/viajes",
        json={"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
        headers=headers,
    )
    assert r.status_code in (200, 201), r.text
    tipos = [v["tipo"] for v in client.get(f"{API}/servicios/{creado['id']}", headers=headers).json()["viajes"]]
    assert tipos == ["recoleccion", "entrega"]


def test_quitar_viaje_terminado_borra_sus_datos_y_el_servicio_lo_refleja(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    s = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    recoleccion, entrega = s["viajes"][0]["id"], s["viajes"][1]["id"]
    client.post(f"{API}/viajes/{entrega}/terminar", json={"referencia_acuse": "FOLIO-1"}, headers=headers)
    assert client.get(f"{API}/servicios/{s['id']}", headers=headers).json()["viajes"][1]["estado"] == "terminado"

    r = client.delete(f"{API}/viajes/{entrega}", headers=headers)
    assert r.status_code == 204, r.text
    detalle = client.get(f"{API}/servicios/{s['id']}", headers=headers).json()
    assert [v["id"] for v in detalle["viajes"]] == [recoleccion]


def test_acuse_escaneado_solo_un_pdf(client: TestClient, admin_user: Usuario, monkeypatch):
    from app.modules.servicios import router as servicios_router

    monkeypatch.setattr(servicios_router, "subir_archivo", lambda *a, **k: None)
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    s = client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()
    entrega = s["viajes"][1]["id"]

    foto = client.post(
        f"{API}/viajes/{entrega}/acuses", files={"file": ("acuse.jpg", b"\xff\xd8\xff fake", "image/jpeg")}, headers=headers
    )
    assert foto.status_code == 422 and foto.json()["error"]["details"][0]["issue"] == "solo_pdf"

    for nombre in ("primero.pdf", "segundo.pdf"):
        r = client.post(
            f"{API}/viajes/{entrega}/acuses", files={"file": (nombre, b"%PDF-1.7 fake", "application/pdf")}, headers=headers
        )
        assert r.status_code == 201, r.text
    acuses = client.get(f"{API}/servicios/{s['id']}", headers=headers).json()["viajes"][1]["acuses"]
    assert len([a for a in acuses if a["tipo"] == "escaneo"]) == 1  # el segundo reemplaza al primero


def test_editar_servicio_completo_como_lo_hace_la_pantalla(
    client: TestClient, admin_user: Usuario, session: Session
):
    """Mismo orden que la pantalla Editar: cabecera, quitar, modificar y agregar viajes."""
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    otro_destino = client.post(
        f"{API}/catalogos/lugares",
        json={"nombre": "Qualtia", "estado": "MEX", "codigo_postal": "54000"},
        headers=headers,
    ).json()
    otra_unidad = client.post(
        f"{API}/catalogos/unidades",
        json={"apodo": "Nissan Gris", "placa": "AB1234C", "config_vehicular": "VL",
              "peso_bruto_vehicular": 0.5, "perm_sct": "TPAF14", "num_permiso_sct": "XYZ123"},
        headers=headers,
    ).json()
    s = client.post(
        f"{API}/servicios",
        json=_servicio_payload(
            cat,
            viajes=[
                {"tipo": "recoleccion", "origen_lugar_id": cat["origen"]["id"]},
                {"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"], "distancia_km": 70},
                {"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"], "distancia_km": 70},
            ],
        ),
        headers=headers,
    ).json()
    sid = s["id"]
    origen, entrega1, entrega2 = (v["id"] for v in s["viajes"])

    # 1) cabecera: unidad, fecha, notas y precio
    r = client.patch(
        f"{API}/servicios/{sid}",
        json={"unidad_id": otra_unidad["id"], "fecha": "2026-11-05", "notas": "cambio", "subtotal": 4600},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    # 2) quitar la segunda entrega, 3) cambiar el destino/km/CP de la primera, 4) agregar otra
    assert client.delete(f"{API}/viajes/{entrega2}", headers=headers).status_code == 204
    r = client.patch(
        f"{API}/viajes/{entrega1}",
        json={"destino_lugar_id": otro_destino["id"], "distancia_km": 220, "destino_cp": "50000",
              "notas_admin": "portón 3"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"{API}/servicios/{sid}/viajes",
        json={"tipo": "entrega", "destino_lugar_id": cat["destino"]["id"], "distancia_km": 15},
        headers=headers,
    )
    assert r.status_code == 201, r.text

    d = client.get(f"{API}/servicios/{sid}", headers=headers).json()
    assert d["unidad"]["apodo"] == "Nissan Gris" and d["fecha"] == "2026-11-05"
    assert d["notas"] == "cambio" and float(d["subtotal"]) == 4600
    assert [v["tipo"] for v in d["viajes"]] == ["recoleccion", "entrega", "entrega"]
    assert d["viajes"][0]["id"] == origen
    e1, e2 = d["viajes"][1], d["viajes"][2]
    assert (e1["destino"]["nombre"], e1["distancia_km"], e1["destino_cp"], e1["notas_admin"]) == (
        "Qualtia", 220, "50000", "portón 3")
    assert (e2["destino"]["nombre"], e2["distancia_km"]) == ("Tiendas Express", 15)
    assert d["estado"] == "programado" and "cancelar" in d["acciones_permitidas"]

    # Quitar el CP propio y el km: null explícito los borra.
    client.patch(f"{API}/viajes/{entrega1}", json={"destino_cp": None, "distancia_km": None}, headers=headers)
    e1 = client.get(f"{API}/servicios/{sid}", headers=headers).json()["viajes"][1]
    assert e1["destino_cp"] is None and e1["distancia_km"] is None

    # Un viaje terminado también se corrige (lugar y km).
    client.post(f"{API}/viajes/{entrega1}/terminar", json={"referencia_acuse": "F-1"}, headers=headers)
    r = client.patch(f"{API}/viajes/{entrega1}", json={"distancia_km": 99}, headers=headers)
    assert r.status_code == 200 and r.json()["distancia_km"] == 99

    # Timbrado anticipado con precio exige subtotal; apagarlo con el servicio sin precio sí se puede.
    r = client.patch(f"{API}/servicios/{sid}", json={"timbrado_anticipado": True, "subtotal": None}, headers=headers)
    assert r.status_code == 422
    r = client.patch(f"{API}/servicios/{sid}", json={"timbrado_anticipado": True, "subtotal": 4600}, headers=headers)
    assert r.status_code == 200 and r.json()["timbrado_anticipado"] is True

    # Con factura vigente la edición fiscal queda bloqueada (409), solo las notas siguen abiertas.
    session.add(Factura(servicio_id=uuid.UUID(sid), cliente_id=uuid.UUID(cat["cliente"]["id"]),
                        estado=EstadoFactura.timbrada, serie="ELG", folio="1", metodo_pago="PPD",
                        uso_cfdi="G03", subtotal=4600, iva_trasladado=736, iva_retenido=184,
                        total=5152, saldo_insoluto=5152))
    session.commit()
    assert client.patch(f"{API}/servicios/{sid}", json={"subtotal": 1}, headers=headers).status_code == 409
    assert client.patch(f"{API}/viajes/{entrega1}", json={"distancia_km": 1}, headers=headers).status_code == 409
    assert client.patch(f"{API}/servicios/{sid}", json={"notas": "ok"}, headers=headers).status_code == 200
    detalle = client.get(f"{API}/servicios/{sid}", headers=headers).json()
    assert detalle["datos_fiscales_bloqueados"] is True


def test_terminar_en_bloque_sin_acuse_y_con_fallos_aislados(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, headers)
    ids = [
        client.post(f"{API}/servicios", json=_servicio_payload(cat), headers=headers).json()["id"]
        for _ in range(3)
    ]
    # Uno ya con su primer viaje terminado (se completa solo el pendiente), otro cancelado.
    previo = client.get(f"{API}/servicios/{ids[0]}", headers=headers).json()
    client.post(f"{API}/viajes/{previo['viajes'][0]['id']}/terminar", json={}, headers=headers)
    client.post(f"{API}/servicios/{ids[2]}/cancelar", json={"motivo": "x"}, headers=headers)

    r = client.post(f"{API}/servicios/terminar-en-bloque", json={"servicio_ids": [*ids, ids[0]]}, headers=headers)
    assert r.status_code == 200, r.text
    res = r.json()["resultados"]
    assert [(x["ok"], x["viajes_terminados"]) for x in res] == [(True, 1), (True, 2), (False, 0)]
    assert "cancelado" in res[2]["error"]

    for sid in ids[:2]:
        d = client.get(f"{API}/servicios/{sid}", headers=headers).json()
        assert d["estado"] == "terminado" and all(v["estado"] == "terminado" for v in d["viajes"])
        assert "facturar" in d["acciones_permitidas"]
        entrega = d["viajes"][1]
        assert entrega["acuse_requerido"] and not entrega["acuse_completo"]  # acuse pendiente, se sube después
    # El cancelado sigue cancelado; repetir sobre uno ya terminado no rompe nada.
    assert client.get(f"{API}/servicios/{ids[2]}", headers=headers).json()["estado"] == "cancelado"
    r2 = client.post(f"{API}/servicios/terminar-en-bloque", json={"servicio_ids": [ids[0]]}, headers=headers)
    assert r2.json()["resultados"][0]["ok"] is False
    assert client.post(f"{API}/servicios/terminar-en-bloque", json={"servicio_ids": []}, headers=headers).status_code == 422
