"""Tarifario fijo de Chemital (nivel 1 del sugeridor) + `/configuracion`."""
from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario
from app.modules.configuracion.service import DEFAULTS
from app.modules.precios import tarifario
from tests.test_facturacion import API, _auth_headers, _servicio_payload, _setup_catalogos

TARIFARIO = DEFAULTS["precio.tarifario_cliente"]


def _total(lineas):
    return sum((l.monto for l in lineas), Decimal(0))


def test_cp_cdmx():
    assert tarifario.cp_es_cdmx("01000") and tarifario.cp_es_cdmx("16999") and tarifario.cp_es_cdmx("06600")
    assert not tarifario.cp_es_cdmx("52000") and not tarifario.cp_es_cdmx("17000")
    assert not tarifario.cp_es_cdmx(None) and not tarifario.cp_es_cdmx("abc")


def test_tier_por_tonelaje():
    assert tarifario.tier_de_unidad(0.5) == "saveiro"
    assert tarifario.tier_de_unidad(1) == "nissan"
    assert tarifario.tier_de_unidad(3.5) == "ram"
    assert tarifario.tier_de_unidad(10) is None  # Rabón, sin tarifa


def test_un_destino_cdmx_por_unidad():
    for tier, esperado in [("saveiro", 1650), ("nissan", 2200), ("ram", 2970)]:
        assert _total(tarifario.calcular(TARIFARIO, tier, ["06600"])) == esperado


def test_destinos_adicionales():
    # CDMX + 2 tiros más
    assert _total(tarifario.calcular(TARIFARIO, "saveiro", ["06600", "52000", "06700"])) == 1650 + 2 * 660
    assert _total(tarifario.calcular(TARIFARIO, "ram", ["06600", "52000"])) == 2970 + 990


def test_sin_cdmx_o_sin_tarifa_no_aplica():
    assert tarifario.calcular(TARIFARIO, "saveiro", ["52000"]) is None
    assert tarifario.calcular(TARIFARIO, None, ["06600"]) is None


def test_cliente_aplica_por_nombre():
    assert tarifario.cliente_aplica(TARIFARIO, ["Chemital", "CHEMITAL DE MEXICO"])
    assert not tarifario.cliente_aplica(TARIFARIO, ["Aerzen"])


def test_configuracion_get_y_patch_tarifario(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    assert client.get(f"{API}/configuracion", headers=h).json()["precio.tarifario_cliente"] == TARIFARIO
    nuevo = {
        "cliente": "chemital",
        "tarifas": {
            "saveiro": {"cdmx": 1700, "extra": 700},
            "nissan": {"cdmx": 2200, "extra": 660},
            "ram": {"cdmx": 2970, "extra": 990},
        },
    }
    r = client.patch(f"{API}/configuracion", json={"precio.tarifario_cliente": nuevo}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["precio.tarifario_cliente"]["tarifas"]["saveiro"]["cdmx"] == 1700
    malo = {**nuevo, "tarifas": {"saveiro": {"cdmx": -1, "extra": 1}}}
    assert client.patch(f"{API}/configuracion", json={"precio.tarifario_cliente": malo}, headers=h).status_code == 422
    assert client.patch(f"{API}/configuracion", json={"otra.clave": 1}, headers=h).status_code == 422


def test_sugerencia_de_facturacion_usa_tarifario(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    cat = _setup_catalogos(client, h)
    cdmx = client.post(
        f"{API}/catalogos/lugares",
        json={"nombre": "Bodega CDMX", "estado": "CMX", "codigo_postal": "06600"},
        headers=h,
    ).json()
    payload = _servicio_payload(cat)
    payload["viajes"][1]["destino_lugar_id"] = cdmx["id"]
    s = client.post(f"{API}/servicios", json=payload, headers=h)
    assert s.status_code in (200, 201), s.text
    det = client.get(f"{API}/servicios/{s.json()['id']}/facturacion", headers=h).json()
    sug = det["precio_sugerido"]
    assert sug["fuente"] == "tarifa_pactada"
    assert Decimal(sug["monto"]) == 1650  # Saveiro (0.5 t) a CDMX
