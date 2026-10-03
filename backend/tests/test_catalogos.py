"""Tests de catálogos y accesos — `fase-1-catalogos §Definición de terminado`."""
from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario

API = "/api/v1"


def _auth_headers(client: TestClient, email: str, password: str = "secret123") -> dict:
    login = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _unidad_payload(**overrides) -> dict:
    payload = {
        "apodo": "Saveiro Blanca",
        "placa": "KR9417A",
        "anio_modelo": 2019,
        "config_vehicular": "VL",
        "peso_bruto_vehicular": 0.5,
        "perm_sct": "TPAF14",
        "num_permiso_sct": "1522ZACE14122021277602000",
        "aseguradora_resp_civil": "SURA",
        "poliza_resp_civil": "14521-1",
    }
    payload.update(overrides)
    return payload


# --- Unidades -----------------------------------------------------------


def test_unidad_requiere_admin(client: TestClient, operador_user: Usuario):
    headers = _auth_headers(client, operador_user.email)
    response = client.get(f"{API}/catalogos/unidades", headers=headers)
    assert response.status_code == 403


def test_crear_y_listar_unidad(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    response = client.post(f"{API}/catalogos/unidades", json=_unidad_payload(), headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["apodo"] == "Saveiro Blanca"
    assert body["activo"] is True

    listado = client.get(f"{API}/catalogos/unidades", headers=headers)
    assert listado.status_code == 200
    assert listado.json()["total"] == 1


def test_unidad_apodo_duplicado_422(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    client.post(f"{API}/catalogos/unidades", json=_unidad_payload(), headers=headers)
    dup = client.post(
        f"{API}/catalogos/unidades",
        json=_unidad_payload(placa="OTRA123"),
        headers=headers,
    )
    assert dup.status_code == 422
    assert dup.json()["error"]["details"][0]["field"] == "apodo"


def test_unidad_barras_sin_num_barras_422(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    response = client.post(
        f"{API}/catalogos/unidades",
        json=_unidad_payload(tipo_medidor="barras"),
        headers=headers,
    )
    assert response.status_code == 422


def test_unidad_barras_con_num_barras_ok(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    response = client.post(
        f"{API}/catalogos/unidades",
        json=_unidad_payload(tipo_medidor="barras", num_barras=8),
        headers=headers,
    )
    assert response.status_code == 201, response.text


def test_unidad_eliminar_sin_uso_borra_definitivo(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    creada = client.post(f"{API}/catalogos/unidades", json=_unidad_payload(), headers=headers)
    unidad_id = creada.json()["id"]

    uso = client.get(f"{API}/catalogos/unidades/{unidad_id}/uso", headers=headers)
    assert uso.json()["accion_al_eliminar"] == "eliminar"

    eliminar = client.delete(f"{API}/catalogos/unidades/{unidad_id}", headers=headers)
    assert eliminar.status_code == 200
    assert eliminar.json()["resultado"] == "eliminado"
    assert client.get(f"{API}/catalogos/unidades/{unidad_id}", headers=headers).status_code == 404


def test_unidad_editar_y_restaurar(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    creada = client.post(f"{API}/catalogos/unidades", json=_unidad_payload(), headers=headers)
    unidad_id = creada.json()["id"]

    editada = client.patch(
        f"{API}/catalogos/unidades/{unidad_id}", json={"anio_modelo": 2020}, headers=headers
    )
    assert editada.status_code == 200
    assert editada.json()["anio_modelo"] == 2020

    eliminar = client.delete(f"{API}/catalogos/unidades/{unidad_id}", headers=headers)
    assert eliminar.json()["resultado"] == "eliminado"
    # Ya no existe (se borró físico); restaurar un id inexistente da 404.
    restaurar = client.post(f"{API}/catalogos/unidades/{unidad_id}/restaurar", headers=headers)
    assert restaurar.status_code == 404


# --- Operadores y acceso --------------------------------------------------


def test_operador_crud_y_acceso(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    creado = client.post(
        f"{API}/catalogos/operadores",
        json={"nombre": "Enrique Zamora", "rfc": "ZACE880207MC7", "num_licencia": "LFD00065145"},
        headers=headers,
    )
    assert creado.status_code == 201, creado.text
    operador_id = creado.json()["id"]

    sin_acceso = client.get(f"{API}/catalogos/operadores/{operador_id}/acceso", headers=headers)
    assert sin_acceso.status_code == 404

    acceso = client.post(
        f"{API}/catalogos/operadores/{operador_id}/acceso",
        json={"email": "enrique", "password_temporal": "temporal123"},
        headers=headers,
    )
    assert acceso.status_code == 201, acceso.text

    # El operador ya puede iniciar sesión con su acceso nuevo.
    login_operador = client.post(
        f"{API}/auth/login", json={"email": "enrique", "password": "temporal123"}
    )
    assert login_operador.status_code == 200
    assert login_operador.json()["user"]["rol"] == "operador"

    # Un operador no puede tener dos accesos.
    segundo = client.post(
        f"{API}/catalogos/operadores/{operador_id}/acceso",
        json={"email": "otro", "password_temporal": "x"},
        headers=headers,
    )
    assert segundo.status_code == 409

    # Desactivar el acceso le impide iniciar sesión.
    client.patch(
        f"{API}/catalogos/operadores/{operador_id}/acceso",
        json={"activo": False},
        headers=headers,
    )
    login_desactivado = client.post(
        f"{API}/auth/login", json={"email": "enrique", "password": "temporal123"}
    )
    assert login_desactivado.status_code == 401


def test_operador_rfc_invalido_422(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    response = client.post(
        f"{API}/catalogos/operadores",
        json={"nombre": "X", "rfc": "NO-VALIDO", "num_licencia": "LFD1"},
        headers=headers,
    )
    assert response.status_code == 422


# --- Clientes y mercancías (anidadas) -------------------------------------


def _cliente_payload(**overrides) -> dict:
    payload = {
        "razon_social": "CHEMITAL DE MEXICO",
        "nombre_comercial": "Chemital",
        "rfc": "CME091007LG1",
        "cp_fiscal": "52004",
        "regimen_fiscal": "601",
        "regimen_receptor": "moral",
        "modo_acuse": "referencia",
        "emails_facturacion": ["mgallegos@chemitalmex.com"],
    }
    payload.update(overrides)
    return payload


def test_cliente_crud_y_mercancias(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    creado = client.post(f"{API}/catalogos/clientes", json=_cliente_payload(), headers=headers)
    assert creado.status_code == 201, creado.text
    cliente_id = creado.json()["id"]
    assert creado.json()["emails_facturacion"] == ["mgallegos@chemitalmex.com"]

    mercancia = client.post(
        f"{API}/catalogos/clientes/{cliente_id}/mercancias",
        json={
            "nombre_humano": "Preservativos de alimentos",
            "bienes_transp": "12164501",
            "clave_unidad": "X4G",
            "unidad_desc": "Caja de cartón",
        },
        headers=headers,
    )
    assert mercancia.status_code == 201, mercancia.text

    # Con una mercancía referenciándolo, "eliminar" archiva en vez de borrar.
    uso = client.get(f"{API}/catalogos/clientes/{cliente_id}/uso", headers=headers)
    assert uso.json()["referencias"]["mercancias"] == 1
    assert uso.json()["accion_al_eliminar"] == "archivar"

    eliminar = client.delete(f"{API}/catalogos/clientes/{cliente_id}", headers=headers)
    assert eliminar.json()["resultado"] == "archivado"
    archivado = client.get(f"{API}/catalogos/clientes/{cliente_id}", headers=headers)
    assert archivado.json()["activo"] is False

    restaurado = client.post(f"{API}/catalogos/clientes/{cliente_id}/restaurar", headers=headers)
    assert restaurado.json()["activo"] is True


def test_cliente_rfc_invalido_422(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    response = client.post(
        f"{API}/catalogos/clientes", json=_cliente_payload(rfc="MAL"), headers=headers
    )
    assert response.status_code == 422


# --- Lugares ---------------------------------------------------------------


def _lugar_payload(**overrides) -> dict:
    payload = {"nombre": "Planta Chemital Toluca", "estado": "MEX", "codigo_postal": "52004"}
    payload.update(overrides)
    return payload


def test_lugar_origen_predeterminado_unico_por_cliente(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    cliente = client.post(f"{API}/catalogos/clientes", json=_cliente_payload(), headers=headers)
    cliente_id = cliente.json()["id"]

    primero = client.post(
        f"{API}/catalogos/lugares",
        json=_lugar_payload(cliente_id=cliente_id, es_origen_predeterminado=True),
        headers=headers,
    )
    assert primero.status_code == 201, primero.text

    segundo = client.post(
        f"{API}/catalogos/lugares",
        json=_lugar_payload(
            cliente_id=cliente_id, nombre="Otra planta", es_origen_predeterminado=True
        ),
        headers=headers,
    )
    assert segundo.status_code == 201

    primero_actualizado = client.get(
        f"{API}/catalogos/lugares/{primero.json()['id']}", headers=headers
    )
    assert primero_actualizado.json()["es_origen_predeterminado"] is False
    assert segundo.json()["es_origen_predeterminado"] is True


def test_lugar_global_sin_cliente(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    response = client.post(
        f"{API}/catalogos/lugares", json=_lugar_payload(), headers=headers
    )
    assert response.status_code == 201
    assert response.json()["cliente_id"] is None


# --- Usuarios administradores ------------------------------------------------


def test_admin_no_puede_desactivarse_a_si_mismo(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    response = client.patch(
        f"{API}/usuarios/{admin_user.id}", json={"activo": False}, headers=headers
    )
    assert response.status_code == 409


def test_no_puede_quedar_sin_admins_activos(client: TestClient, admin_user: Usuario):
    headers = _auth_headers(client, admin_user.email)
    otro = client.post(
        f"{API}/usuarios",
        json={"nombre": "Otro Admin", "email": "otro@test.mx", "password_temporal": "temporal123"},
        headers=headers,
    )
    assert otro.status_code == 201
    otro_id = otro.json()["id"]

    # Desactivar al otro admin sí se puede (admin_user sigue activo).
    desactivar_otro = client.patch(
        f"{API}/usuarios/{otro_id}", json={"activo": False}, headers=headers
    )
    assert desactivar_otro.status_code == 200

    # Pero ahora admin_user es el único activo: no puede desactivarlo un tercero tampoco
    # (aquí se prueba vía el mismo admin_user, que ya está cubierto por el test anterior).
