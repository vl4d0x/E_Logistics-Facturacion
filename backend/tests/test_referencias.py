"""REF repetida en otro servicio del mismo cliente y servicios de días cercanos (solo avisos)."""
from fastapi.testclient import TestClient

from app.modules.auth.models import Usuario
from app.modules.servicios.referencias import normalizar_ref
from tests.test_operacion import API, _auth_headers, _setup


def _otro_servicio(client, h, ctx, fecha="2026-10-04"):
    s = ctx["servicio"]
    return client.post(
        f"{API}/servicios",
        json={
            "cliente_id": ctx["cliente"]["id"],
            "unidad_id": ctx["unidad"]["id"],
            "operador_id": ctx["operador"]["id"],
            "fecha": fecha,
            "viajes": [
                {"tipo": "recoleccion", "origen_lugar_id": s["viajes"][0]["origen"]["id"]},
                {"tipo": "entrega", "destino_lugar_id": s["viajes"][1]["destino"]["id"], "distancia_km": 70},
            ],
        },
        headers=h,
    ).json()


def test_normalizar_ref():
    assert normalizar_ref(" 05151 ") == normalizar_ref("5151") == "5151"
    assert normalizar_ref("a-12") == "A-12"
    assert normalizar_ref("000") == "000"


def test_ref_repetida_avisa_en_facturar_y_por_api(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    ctx = _setup(client, h)
    client.patch(f"{API}/catalogos/clientes/{ctx['cliente']['id']}", json={"requiere_folio_concepto": True}, headers=h)
    primero = ctx["servicio"]
    client.put(f"{API}/viajes/{primero['viajes'][1]['id']}/folio", json={"folio": "5151"}, headers=h)

    segundo = _otro_servicio(client, h, ctx)
    client.put(f"{API}/viajes/{segundo['viajes'][1]['id']}/folio", json={"folio": "05151"}, headers=h)

    checks = {c["regla"]: c for c in client.get(f"{API}/servicios/{segundo['id']}/validar", headers=h).json()["checks"]}
    assert checks["ref_repetida"]["nivel"] == "warning"
    assert f"#{primero['numero']}" in checks["ref_repetida"]["mensaje"]
    folios = client.get(f"{API}/servicios/{segundo['id']}/facturacion", headers=h).json()["concepto"]["folios"]
    assert folios[0]["repetida_en"][0]["numero"] == primero["numero"]

    r = client.get(f"{API}/clientes/{ctx['cliente']['id']}/referencias-repetidas?ref=5151&ref=999", headers=h).json()
    assert list(r["repetidas"]) == ["5151"] and len(r["repetidas"]["5151"]) == 2

    # Cancelado no cuenta.
    client.post(f"{API}/servicios/{primero['id']}/cancelar", json={"motivo": "prueba"}, headers=h)
    checks = {c["regla"]: c for c in client.get(f"{API}/servicios/{segundo['id']}/validar", headers=h).json()["checks"]}
    assert checks["ref_repetida"]["nivel"] == "ok"


def test_operador_ve_aviso_de_folio_repetido(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    ctx = _setup(client, h)
    otro = _otro_servicio(client, h, ctx)
    client.put(f"{API}/viajes/{otro['viajes'][1]['id']}/folio", json={"folio": "7777"}, headers=h)
    entrega = ctx["servicio"]["viajes"][1]["id"]
    oh = ctx["operador_headers"]
    r = client.get(f"{API}/operador/viajes/{entrega}/referencia-repetida?ref=7777", headers=oh).json()
    assert r["repetida"] is True and r["servicios"][0]["numero"] == otro["numero"]
    assert client.get(f"{API}/operador/viajes/{entrega}/referencia-repetida?ref=1", headers=oh).json()["repetida"] is False


def test_servicios_cercanos(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    ctx = _setup(client, h)  # servicio del 2026-10-03
    cerca = _otro_servicio(client, h, ctx, fecha="2026-10-06")
    _otro_servicio(client, h, ctx, fecha="2026-10-10")
    r = client.get(f"{API}/clientes/{ctx['cliente']['id']}/servicios-cercanos?fecha=2026-10-04", headers=h).json()
    assert r["dias"] == 3
    assert {s["numero"] for s in r["servicios"]} == {ctx["servicio"]["numero"], cerca["numero"]}
    r = client.get(
        f"{API}/clientes/{ctx['cliente']['id']}/servicios-cercanos?fecha=2026-10-04&excluir_servicio_id={cerca['id']}",
        headers=h,
    ).json()
    assert [s["numero"] for s in r["servicios"]] == [ctx["servicio"]["numero"]]
