"""Cliente que usa los lugares y mercancías de otro (AERZEN RENTAL → AERZEN)."""
from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario
from tests.test_facturacion import API, _auth_headers, _servicio_payload, _setup_catalogos


def _rental(client, h, padre_id, **extra):
    return client.post(
        f"{API}/catalogos/clientes",
        json={
            "razon_social": "AERZEN RENTAL MEXICO ",
            "nombre_comercial": " AERZEN RENTAL ",
            "rfc": "ARM231214NK0",
            "cp_fiscal": "52360",
            "regimen_fiscal": "601",
            "regimen_receptor": "moral",
            "modo_acuse": "escaneo",
            "hereda_de_id": padre_id,
            **extra,
        },
        headers=h,
    )


def test_hereda_lugares_y_mercancias_y_crea_servicio(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, h)
    r = _rental(client, h, cat["cliente"]["id"])
    assert r.status_code == 201, r.text
    rental = r.json()
    assert rental["nombre_comercial"] == "AERZEN RENTAL"  # sin espacios sobrantes
    assert rental["hereda_de_id"] == cat["cliente"]["id"]

    lugares = client.get(f"{API}/catalogos/lugares?cliente_id={rental['id']}", headers=h).json()
    assert {l["id"] for l in lugares} >= {cat["origen"]["id"], cat["destino"]["id"]}
    mercancias = client.get(f"{API}/catalogos/clientes/{rental['id']}/mercancias", headers=h).json()
    assert [m["id"] for m in mercancias] == [cat["mercancia"]["id"]]

    # Un servicio de la otra razón social puede usar el origen del cliente padre.
    r = client.post(f"{API}/servicios", json=_servicio_payload(cat, cliente_id=rental["id"]), headers=h)
    assert r.status_code == 201, r.text


def test_sin_herencia_el_lugar_de_otro_cliente_se_rechaza(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, h)
    otro = _rental(client, h, None).json()
    r = client.post(f"{API}/servicios", json=_servicio_payload(cat, cliente_id=otro["id"]), headers=h)
    assert r.status_code == 422


def test_herencia_de_un_solo_nivel(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, h)
    padre_id = cat["cliente"]["id"]
    rental = _rental(client, h, padre_id).json()
    # ni de sí mismo, ni de alguien que ya hereda, ni el padre puede heredar a su vez
    assert client.patch(f"{API}/catalogos/clientes/{rental['id']}", json={"hereda_de_id": rental["id"]}, headers=h).status_code == 422
    assert _rental(client, h, rental["id"], rfc="XYZ231214NK0").status_code == 422
    assert client.patch(f"{API}/catalogos/clientes/{padre_id}", json={"hereda_de_id": rental["id"]}, headers=h).status_code == 422
    # se puede quitar
    r = client.patch(f"{API}/catalogos/clientes/{rental['id']}", json={"hereda_de_id": None}, headers=h)
    assert r.status_code == 200 and r.json()["hereda_de_id"] is None
