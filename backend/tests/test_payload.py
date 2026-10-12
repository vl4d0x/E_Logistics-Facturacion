"""`04-facturacion-cfdi §1-4.5` (H4.2) — payload puro, sin red.

El test de equivalencia compara contra un CFDI real de Chemital
(`.misc/CME091007LG1_SS_5318_20260820.xml`, privado/gitignored); se salta si el
archivo no está presente (otros checkouts, CI).
"""
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.facturacion.payload import (
    construir_carta_porte,
    construir_items,
    construir_payload_cfdi,
)

FIXTURE = Path(__file__).parents[2] / ".misc" / "CME091007LG1_SS_5318_20260820.xml"

_NS = {
    "cfdi": "http://www.sat.gob.mx/cfd/4",
    "cp": "http://www.sat.gob.mx/CartaPorte31",
}


def _montos() -> dict[str, Decimal]:
    return {
        "subtotal": Decimal("1650.00"),
        "iva_trasladado": Decimal("264.00"),
        "iva_retenido": Decimal("66.00"),
        "total": Decimal("1848.00"),
    }


def _receptor() -> dict:
    return {
        "razon_social": "CHEMITAL DE MEXICO",
        "rfc": "CME091007LG1",
        "cp_fiscal": "52004",
        "regimen_fiscal": "601",
        "regimen_receptor": "moral",
        "uso_cfdi": "G03",
        "metodo_pago": "PPD",
        "forma_pago": "99",
    }


def test_construir_items_incluye_iva_y_retencion_moral():
    items = construir_items({"descripcion": "FLETE X"}, _montos(), es_moral=True)
    assert len(items) == 1
    item = items[0]
    assert item["ProductCode"] == "78101802"
    assert item["UnitCode"] == "SX"
    assert item["Subtotal"] == "1650.00"
    assert item["Total"] == "1848.00"
    nombres = {t["Name"] for t in item["Taxes"]}
    assert nombres == {"IVA", "IVA RET"}


def test_construir_items_sin_retencion_persona_fisica():
    items = construir_items({"descripcion": "FLETE X"}, _montos(), es_moral=False)
    nombres = {t["Name"] for t in items[0]["Taxes"]}
    assert nombres == {"IVA"}


def test_cantidad_se_recorta_a_seis_decimales():
    """Encontrado probando contra el sandbox real: `NUMERIC` sin escala fija manda
    "1.0000000000" y Facturama lo rechaza (máximo 6 decimales)."""
    carta_porte = construir_carta_porte(
        ubicaciones=[],
        mercancias=[
            {
                "bienes_transp": "12164501",
                "descripcion": "Preservativos de alimentos",
                "cantidad": Decimal("1.0000000000"),
                "clave_unidad": "X4G",
                "unidad_desc": None,
                "peso_kg": 20.0,
            }
        ],
        autotransporte={
            "perm_sct": "TPAF14",
            "num_permiso_sct": "1522ZACE14122021277602000",
            "config_vehicular": "VL",
            "peso_bruto_vehicular": 0.5,
            "placa": "9957ZP",
            "anio_modelo": None,
            "aseguradora": None,
            "poliza": None,
        },
        figura={"nombre": "ENRIQUE", "rfc": "ZACE880207MC7", "num_licencia": "LFD00065145"},
        total_dist_rec=80.0,
    )
    assert carta_porte["Mercancias"]["Mercancia"][0]["Cantidad"] == "1"
    assert carta_porte["Mercancias"]["PesoBrutoTotal"] == "20"


def test_construir_payload_cfdi_estructura_completa():
    payload = construir_payload_cfdi(
        serie="ELG",
        expedition_place="52176",
        receptor=_receptor(),
        concepto={"descripcion": "FLETE UNIDAD 05 TON\nORIGEN: CHEMITAL\nDESTINO: GUADALUPE LIMON\nFECHA: 11 AGO 26"},
        montos=_montos(),
        ubicaciones=[
            {
                "tipo": "Origen",
                "lugar": {
                    "rfc_remitente_destinatario": "CME091007LG1",
                    "nombre_remitente_destinatario": None,
                    "calle": None,
                    "num_exterior": None,
                    "colonia": None,
                    "municipio_clave": "051",
                    "localidad_clave": None,
                    "estado": "MEX",
                    "pais": "MEX",
                    "codigo_postal": "52004",
                },
                "fecha_hora": None,
            },
            {
                "tipo": "Destino",
                "lugar": {
                    "rfc_remitente_destinatario": "XAXX010101000",
                    "nombre_remitente_destinatario": "GUADALUPE LIMON",
                    "calle": None,
                    "num_exterior": None,
                    "colonia": None,
                    "municipio_clave": "051",
                    "localidad_clave": None,
                    "estado": "MEX",
                    "pais": "MEX",
                    "codigo_postal": "52000",
                },
                "fecha_hora": None,
                "distancia_km": 80.0,
            },
        ],
        mercancias=[
            {
                "bienes_transp": "12164501",
                "descripcion": "Preservativos de alimentos",
                "cantidad": Decimal(1),
                "clave_unidad": "X4G",
                "unidad_desc": None,
                "peso_kg": 20.0,
            }
        ],
        autotransporte={
            "perm_sct": "TPAF14",
            "num_permiso_sct": "1522ZACE14122021277602000",
            "config_vehicular": "VL",
            "peso_bruto_vehicular": 0.5,
            "placa": "9957ZP",
            "anio_modelo": 2019,
            "aseguradora": "SURA",
            "poliza": "14521-1",
        },
        figura={"nombre": "ENRIQUE", "rfc": "ZACE880207MC7", "num_licencia": "LFD00065145"},
        total_dist_rec=80.0,
    )
    assert payload["ExpeditionPlace"] == "52176"
    assert payload["Receiver"]["Rfc"] == "CME091007LG1"
    cp = payload["Complemento"]["CartaPorte31"]
    assert cp["Ubicaciones"][0]["Domicilio"]["Municipio"] == "051"
    assert cp["Ubicaciones"][1]["DistanciaRecorrida"] == "80"
    assert cp["Mercancias"]["Autotransporte"]["IdentificacionVehicular"]["AnioModeloVM"] == "2019"
    assert cp["FiguraTransporte"][0]["RFCFigura"] == "ZACE880207MC7"


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture privado (.misc/) no disponible en este checkout")
def test_equivalencia_contra_cfdi_real_de_chemital():
    tree = ET.parse(FIXTURE)
    root = tree.getroot()
    receptor_xml = root.find("cfdi:Receptor", _NS)
    concepto_xml = root.find("cfdi:Conceptos/cfdi:Concepto", _NS)
    traslado_xml = concepto_xml.find("cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado", _NS)
    retencion_xml = concepto_xml.find("cfdi:Impuestos/cfdi:Retenciones/cfdi:Retencion", _NS)
    cp_xml = root.find("cfdi:Complemento/cp:CartaPorte", _NS)
    ubicaciones_xml = cp_xml.findall("cp:Ubicaciones/cp:Ubicacion", _NS)
    mercancia_xml = cp_xml.find("cp:Mercancias/cp:Mercancia", _NS)
    autotransporte_xml = cp_xml.find("cp:Mercancias/cp:Autotransporte", _NS)
    figura_xml = cp_xml.find("cp:FiguraTransporte/cp:TiposFigura", _NS)

    assert root.attrib["SubTotal"] == "1650.00"
    assert root.attrib["Total"] == "1848.00"
    assert root.attrib["FormaPago"] == "99"

    receptor = {
        "razon_social": receptor_xml.attrib["Nombre"],
        "rfc": receptor_xml.attrib["Rfc"],
        "cp_fiscal": receptor_xml.attrib["DomicilioFiscalReceptor"],
        "regimen_fiscal": receptor_xml.attrib["RegimenFiscalReceptor"],
        "regimen_receptor": "moral",
        "uso_cfdi": receptor_xml.attrib["UsoCFDI"],
        "metodo_pago": root.attrib["MetodoPago"],
        "forma_pago": root.attrib["FormaPago"],
    }
    montos = {
        "subtotal": Decimal(concepto_xml.attrib["Importe"]),
        "iva_trasladado": Decimal(traslado_xml.attrib["Importe"]),
        "iva_retenido": Decimal(retencion_xml.attrib["Importe"]),
        "total": Decimal(root.attrib["Total"]),
    }

    def _lugar_desde_xml(u) -> dict:
        dom = u.find("cp:Domicilio", _NS)
        return {
            "rfc_remitente_destinatario": u.attrib["RFCRemitenteDestinatario"],
            "nombre_remitente_destinatario": u.attrib.get("NombreRemitenteDestinatario"),
            "calle": dom.attrib.get("Calle"),
            "num_exterior": dom.attrib.get("NumeroExterior"),
            "colonia": dom.attrib.get("Colonia"),
            "municipio_clave": dom.attrib.get("Municipio"),
            "localidad_clave": dom.attrib.get("Localidad"),
            "estado": dom.attrib["Estado"],
            "pais": dom.attrib["Pais"],
            "codigo_postal": dom.attrib["CodigoPostal"],
        }

    ubicaciones = [
        {
            "tipo": u.attrib["TipoUbicacion"],
            "lugar": _lugar_desde_xml(u),
            "fecha_hora": None,
            "distancia_km": float(u.attrib["DistanciaRecorrida"]) if "DistanciaRecorrida" in u.attrib else None,
        }
        for u in ubicaciones_xml
    ]

    payload = construir_payload_cfdi(
        serie="ELG",
        expedition_place=root.attrib["LugarExpedicion"],
        receptor=receptor,
        concepto={"descripcion": concepto_xml.attrib["Descripcion"]},
        montos=montos,
        ubicaciones=ubicaciones,
        mercancias=[
            {
                "bienes_transp": mercancia_xml.attrib["BienesTransp"],
                "descripcion": mercancia_xml.attrib["Descripcion"],
                "cantidad": Decimal(mercancia_xml.attrib["Cantidad"]),
                "clave_unidad": mercancia_xml.attrib["ClaveUnidad"],
                "unidad_desc": mercancia_xml.attrib.get("Unidad"),
                "peso_kg": float(mercancia_xml.attrib["PesoEnKg"]),
            }
        ],
        autotransporte={
            "perm_sct": autotransporte_xml.attrib["PermSCT"],
            "num_permiso_sct": autotransporte_xml.attrib["NumPermisoSCT"],
            "config_vehicular": autotransporte_xml.find("cp:IdentificacionVehicular", _NS).attrib["ConfigVehicular"],
            "peso_bruto_vehicular": 0.5,  # nuestro modelo guarda toneladas; el XML real trae 500 (kg, ver `04 §5`)
            "placa": autotransporte_xml.find("cp:IdentificacionVehicular", _NS).attrib["PlacaVM"],
            "anio_modelo": int(autotransporte_xml.find("cp:IdentificacionVehicular", _NS).attrib["AnioModeloVM"]),
            "aseguradora": autotransporte_xml.find("cp:Seguros", _NS).attrib["AseguraRespCivil"],
            "poliza": autotransporte_xml.find("cp:Seguros", _NS).attrib["PolizaRespCivil"],
        },
        figura={
            "nombre": figura_xml.attrib["NombreFigura"],
            "rfc": figura_xml.attrib["RFCFigura"],
            "num_licencia": figura_xml.attrib["NumLicencia"],
        },
        total_dist_rec=float(cp_xml.attrib["TotalDistRec"]),
    )

    assert payload["Receiver"]["Rfc"] == receptor_xml.attrib["Rfc"]
    assert payload["Receiver"]["Name"] == receptor_xml.attrib["Nombre"]
    assert payload["Receiver"]["CfdiUse"] == receptor_xml.attrib["UsoCFDI"]
    assert payload["Items"][0]["Subtotal"] == concepto_xml.attrib["Importe"]
    assert payload["Items"][0]["Total"] == root.attrib["Total"]
    assert payload["Items"][0]["Taxes"][0]["Total"] == traslado_xml.attrib["Importe"]
    assert payload["Items"][0]["Taxes"][1]["Total"] == retencion_xml.attrib["Importe"]

    cp_payload = payload["Complemento"]["CartaPorte31"]
    assert cp_payload["TotalDistRec"] == cp_xml.attrib["TotalDistRec"]
    assert cp_payload["Ubicaciones"][0]["RFCRemitenteDestinatario"] == ubicaciones_xml[0].attrib["RFCRemitenteDestinatario"]
    assert cp_payload["Ubicaciones"][0]["Domicilio"]["Municipio"] == ubicaciones_xml[0].find("cp:Domicilio", _NS).attrib["Municipio"]
    assert cp_payload["Ubicaciones"][1]["DistanciaRecorrida"] == ubicaciones_xml[1].attrib["DistanciaRecorrida"]
    assert cp_payload["Mercancias"]["Mercancia"][0]["BienesTransp"] == mercancia_xml.attrib["BienesTransp"]
    assert (
        cp_payload["Mercancias"]["Autotransporte"]["IdentificacionVehicular"]["PlacaVM"]
        == autotransporte_xml.find("cp:IdentificacionVehicular", _NS).attrib["PlacaVM"]
    )
    assert cp_payload["FiguraTransporte"][0]["RFCFigura"] == figura_xml.attrib["RFCFigura"]


def test_material_peligroso_no_y_colonia_solo_como_clave():
    from app.modules.facturacion.payload import _domicilio

    base = {"estado": "MEX", "pais": "MEX", "codigo_postal": "52000"}
    assert "Colonia" not in _domicilio({**base, "colonia": "Centro"})  # un nombre lo rechaza el SAT
    assert _domicilio({**base, "colonia": "0412"})["Colonia"] == "0412"

    merc = {"bienes_transp": "51111617", "descripcion": "Medicamento", "cantidad": Decimal(1),
            "clave_unidad": "H87", "unidad_desc": None, "peso_kg": 3.0}
    payload = construir_payload_cfdi(
        serie="ELG", expedition_place="52176", receptor=_receptor(), concepto={"descripcion": "x"},
        montos=_montos(), ubicaciones=[], total_dist_rec=0,
        mercancias=[merc, {**merc, "declarar_material_peligroso": True}],
        autotransporte={"perm_sct": "TPAF01", "num_permiso_sct": "X", "config_vehicular": "VL",
                        "peso_bruto_vehicular": 1, "placa": "A", "anio_modelo": 2019, "aseguradora": "S", "poliza": "P"},
        figura={"nombre": "E", "rfc": "ZACE880207MC7", "num_licencia": "L"},
    )
    m1, m2 = payload["Complemento"]["CartaPorte31"]["Mercancias"]["Mercancia"]
    assert "MaterialPeligroso" not in m1
    assert m2["MaterialPeligroso"] == "No"
