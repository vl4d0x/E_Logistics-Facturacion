"""Facturar con el Excel de registros: búsqueda de destinos, lectura/escritura del Excel y
alta del servicio desde una fila."""
import io
import uuid
import zipfile
from datetime import date

import openpyxl
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.modules.auth.models import Usuario
from app.modules.facturacion.models import EstadoFactura, Factura
from app.modules.registro_excel import excel
from app.modules.registro_excel.matching import Candidato, Indice, partir_destinos
from tests.test_facturacion import API, _auth_headers, _setup_catalogos

ENCABEZADO = ["FECHA", "CLIENTE", "PROP.", "OPERADOR", "UNIDAD", "ORIGEN", "DESTINO", "SUBTOTAL",
              "IVA-RET", "TOTAL", "FACTURA", "REF", "DINORA MENDOZA"]


def _xlsx(filas: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    ws.append(ENCABEZADO)
    for f in filas:
        ws.append(f)
    wb.create_sheet("TAB EJE").append(["no", "es", "esta"])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


# --- Búsqueda ---------------------------------------------------------------------

def _indice():
    nombres = [
        "DISTRIBUIDORA VASSA DIVASSA", "ALIMENTOS Y EMBUTIDOS JARVA", "DAS BESTE", "QUALTIA ALIMENTOS OPERACIONES",
        "EMPACADORA LAS POLVILLAS", "ALIMENTOS PAR", "ALIMENTOS EFA", "COMERCIALIZADORA DE CARNES ROSSPORK",
        "DISTRIBUIDORA DE CARNE MAVA CARR", "THYSSENKRUPP PRESTA DE MEXICO", "EMPACADORA DE CARNES FRIAS HANZ",
        "DISTRIBUIDORA DE CARNES SELECTAS MAG",
    ]
    return Indice([Candidato(i, n) for i, n in enumerate(nombres)])


def _partir(texto):
    return [(g.texto, g.mejor[0].nombre if g.mejor and g.mejor[1] >= 0.8 else None) for g in partir_destinos(texto, _indice())]


def test_destino_abreviado_y_varios_destinos():
    assert _partir("VASSA DIVASA") == [("VASSA DIVASA", "DISTRIBUIDORA VASSA DIVASSA")]
    assert _partir("DAS BESTE, JARVA") == [("DAS BESTE", "DAS BESTE"), ("JARVA", "ALIMENTOS Y EMBUTIDOS JARVA")]
    assert _partir("MAVACARR") == [("MAVACARR", "DISTRIBUIDORA DE CARNE MAVA CARR")]
    assert _partir("THYSSEN KRUPP") == [("THYSSEN KRUPP", "THYSSENKRUPP PRESTA DE MEXICO")]


def test_ciudad_y_notas_no_son_otro_destino():
    assert _partir("TEPOTZOTLAN, QUALTIA") == [("TEPOTZOTLAN, QUALTIA", "QUALTIA ALIMENTOS OPERACIONES")]
    assert _partir("POLVILLAS (TIRO EN FALSO)") == [("POLVILLAS (TIRO EN FALSO)", "EMPACADORA LAS POLVILLAS")]
    # Desconocidos: cada uno es su propio destino.
    assert _partir("THALIA - KORINA") == [("THALIA", None), ("KORINA", None)]
    # Una palabra común sola no basta ("CARNES").
    assert _partir("MUESTRAS SCARNES") == [("MUESTRAS SCARNES", None)]


# --- Excel ------------------------------------------------------------------------

def test_leer_y_escribir_factura_sin_tocar_lo_demas():
    contenido = _xlsx([
        [date(2026, 10, 30), "CHEMITAL", "ENRIQUE", "ENRIQUE", "KICKS", "CHEMITAL", "TIENDAS EXPRESS", 1650, 198, 1848],
        [date(2026, 10, 31), "CHEMITAL", "ENRIQUE", "ENRIQUE", "KICKS", "CHEMITAL", "OTRO", 1650, 198, 1848, 5532],
    ])
    hoja, columnas, filas = excel.leer_registros(contenido)
    assert hoja == "Hoja1" and columnas["factura"] == "K"
    assert filas[0] == (2, {**filas[0][1]}) and filas[0][1]["fecha"] == "2026-10-30" and filas[0][1]["subtotal"] == 1650
    nuevo, escritas = excel.escribir_columna(contenido, hoja, "K", {2: "5540", 3: "9999"})
    assert escritas == [2]  # la fila 3 ya tenía factura: no se sobrescribe
    ws = openpyxl.load_workbook(io.BytesIO(nuevo))["Hoja1"]
    assert ws["K2"].value == 5540 and ws["K3"].value == 5532 and ws["G2"].value == "TIENDAS EXPRESS"
    assert sorted(zipfile.ZipFile(io.BytesIO(nuevo)).namelist()) == sorted(zipfile.ZipFile(io.BytesIO(contenido)).namelist())


# --- Flujo completo ---------------------------------------------------------------

def _preparar(client, h, filas):
    cat = _setup_catalogos(client, h)
    client.patch(f"{API}/catalogos/clientes/{cat['cliente']['id']}", json={"requiere_folio_concepto": True}, headers=h)
    r = client.post(f"{API}/registro-excel", files={"file": ("REGISTROS.xlsx", _xlsx(filas), "application/octet-stream")}, headers=h)
    assert r.status_code == 200, r.text
    return cat


def test_fila_a_servicio_terminado_con_folio_y_destino_nuevo(client: TestClient, admin_user: Usuario, session: Session):
    h = _auth_headers(client, admin_user.email)
    cat = _preparar(client, h, [
        [date(2026, 10, 30), "CHEMITAL", "ENRIQUE", "ENRIQUE", "KICKS", "CHEMITAL", "TIENDAS EXPRES, THALIA", 2310, 277.2, 2587.2, None, None, "820KG"],
    ])
    p = client.get(f"{API}/registro-excel/filas/2", headers=h).json()
    assert p["cliente"]["id"] == cat["cliente"]["id"]
    assert p["operador"]["id"] == cat["operador"]["id"]
    assert p["unidad"]["id"] == cat["unidad"]["id"]  # KICKS = SAVEIRO BLANCA (placa KR9417A)
    assert p["origen"]["lugar"]["id"] == cat["origen"]["id"] and p["origen"]["fuente"] == "predeterminado"
    assert [d["texto"] for d in p["destinos"]] == ["TIENDAS EXPRES", "THALIA"]
    assert p["destinos"][0]["lugar"]["id"] == cat["destino"]["id"]
    assert p["destinos"][1]["lugar"] is None
    assert p["kg_sugerido"] == 820 and p["subtotal"] == "2310.00"
    assert p["mercancia_sugerida_id"] == cat["mercancia"]["id"]

    merc = [{"mercancia_frecuente_id": cat["mercancia"]["id"], "peso_kg": 820}]
    body = {
        "cliente_id": cat["cliente"]["id"], "unidad_id": cat["unidad"]["id"], "operador_id": cat["operador"]["id"],
        "fecha": "2026-10-30", "subtotal": "2310.00",
        "origen": {"texto_excel": "CHEMITAL", "lugar_id": cat["origen"]["id"]},
        "destinos": [
            {"texto_excel": "TIENDAS EXPRES", "lugar_id": cat["destino"]["id"], "folio": "5151", "mercancias": merc},
            {"texto_excel": "THALIA", "nuevo": {"nombre": "thalia"}, "sin_acuse": True, "mercancias": merc},
        ],
    }
    r = client.post(f"{API}/registro-excel/filas/2/servicio", json=body, headers=h)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["estado"] == "terminado" and len(s["viajes"]) == 3
    assert all(v["estado"] == "terminado" for v in s["viajes"])
    nuevo = s["viajes"][2]
    assert nuevo["destino"]["nombre"] == "THALIA" and nuevo["destino"]["rfc_remitente_destinatario"] == "XAXX010101000"
    assert nuevo["destino"]["estado"] == "MEX" and nuevo["distancia_km"] == 70
    assert nuevo["sin_acuse"] is True and nuevo["acuse_completo"] is True

    # Validación: el destino sin REF no bloquea; el concepto lleva solo el folio que sí hay.
    checks = {c["regla"]: c for c in client.get(f"{API}/servicios/{s['id']}/validar", headers=h).json()["checks"]}
    assert checks["acuse_por_entrega"]["nivel"] == "ok"
    assert checks["servicio_terminado"]["nivel"] == "ok"
    concepto = client.get(f"{API}/servicios/{s['id']}/facturacion", headers=h).json()["concepto"]["descripcion"]
    assert "REF: 5151" in concepto and "—" not in concepto.split("REF:")[1]

    # No se crea dos veces; la fila muestra su servicio.
    assert client.post(f"{API}/registro-excel/filas/2/servicio", json=body, headers=h).status_code == 409
    assert client.get(f"{API}/registro-excel/filas/2", headers=h).json()["servicio"]["numero"] == s["numero"]

    # Lo elegido se recuerda: "THALIA" ya sale con su lugar nuevo.
    p2 = client.get(f"{API}/registro-excel/filas/2", headers=h).json()
    assert p2["destinos"][1]["lugar"]["nombre"] == "THALIA" and p2["destinos"][1]["fuente"] == "recordado"

    # Con factura vigente, la descarga escribe el folio en la columna FACTURA.
    session.add(Factura(servicio_id=uuid.UUID(s["id"]), estado=EstadoFactura.timbrada, serie="ELG", folio="5540", metodo_pago="PPD",
                        uso_cfdi="G03", subtotal=2310, iva_trasladado=369.6, iva_retenido=92.4, total=2587.2, saldo_insoluto=2587.2))
    session.commit()
    pend = client.get(f"{API}/registro-excel/filas?pendientes=true", headers=h).json()["items"]
    assert pend == []
    r = client.get(f"{API}/registro-excel/descargar", headers=h)
    assert r.status_code == 200 and r.headers["x-facturas-escritas"] == "1"
    assert openpyxl.load_workbook(io.BytesIO(r.content))["Hoja1"]["K2"].value == 5540


def test_excel_nuevo_reubica_el_servicio_si_se_insertaron_filas(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    fila = [date(2026, 10, 30), "CHEMITAL", "ENRIQUE", "ENRIQUE", "KR9417A SAVEIRO", "CHEMITAL", "TIENDAS EXPRESS", 1650]
    cat = _preparar(client, h, [fila])
    body = {
        "cliente_id": cat["cliente"]["id"], "unidad_id": cat["unidad"]["id"], "operador_id": cat["operador"]["id"],
        "fecha": "2026-10-30", "subtotal": "1650",
        "origen": {"lugar_id": cat["origen"]["id"]},
        "destinos": [{"lugar_id": cat["destino"]["id"], "folio": "1"}],
    }
    s = client.post(f"{API}/registro-excel/filas/2/servicio", json=body, headers=h).json()
    otra = [date(2026, 10, 29), "CHEMITAL", "ENRIQUE", "ENRIQUE", "KR9417A", "CHEMITAL", "OTRO", 900]
    r = client.post(f"{API}/registro-excel", files={"file": ("R2.xlsx", _xlsx([otra, fila]), "application/octet-stream")}, headers=h)
    assert r.json()["registro"]["enlaces_reubicados"] == 1
    assert client.get(f"{API}/registro-excel/filas/3", headers=h).json()["servicio"]["servicio_id"] == s["id"]
    assert client.get(f"{API}/registro-excel/filas/2", headers=h).json()["servicio"] is None


def test_sin_excel_y_archivo_invalido(client: TestClient, admin_user: Usuario):
    h = _auth_headers(client, admin_user.email)
    assert client.get(f"{API}/registro-excel", headers=h).json() == {"registro": None}
    assert client.get(f"{API}/registro-excel/filas/2", headers=h).status_code == 404
    r = client.post(f"{API}/registro-excel", files={"file": ("x.xlsx", b"hola", "application/octet-stream")}, headers=h)
    assert r.status_code == 422
