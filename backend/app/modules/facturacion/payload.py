"""Payload CFDI 4.0 + Carta Porte 3.1 para Facturama — `04-facturacion-cfdi §1-4.5`.

Puro y testeable sin red: recibe datos ya resueltos (incluidas las claves SAT de
Municipio/Localidad, que se resuelven aparte vía Facturama y se cachean en
`lugar.municipio_clave`/`localidad_clave` -- ver `facturacion/service.py`).

Estructura verificada contra el sandbox real de Facturama (payload de prueba
aceptado hasta el paso de sellado) y contra un CFDI real de Chemital
(`.misc/CME091007LG1_SS_5318_20260820.xml`, fixture del test de equivalencia).
"""
import re
from decimal import Decimal
from typing import Any


def _num(valor: Any) -> str:
    """Formatea un número para Facturama: máximo 6 decimales, sin ceros de relleno.

    `ViajeMercancia.cantidad` es `NUMERIC` sin escala fija en Postgres/SQLite, así
    que un `Decimal(1)` puede llegar como "1.0000000000" -- Facturama lo rechaza:
    "el campo cantidad... con valores hasta 6 dígitos decimales" (confirmado contra
    el sandbox real).
    """
    texto = f"{Decimal(str(valor)):.6f}".rstrip("0").rstrip(".")
    return texto or "0"


def _domicilio(lugar: dict[str, Any]) -> dict[str, Any]:
    domicilio: dict[str, Any] = {
        "Estado": lugar["estado"],
        "Pais": lugar.get("pais") or "MEX",
        "CodigoPostal": lugar["codigo_postal"],
    }
    if lugar.get("calle"):
        domicilio["Calle"] = lugar["calle"]
    if lugar.get("num_exterior"):
        domicilio["NumeroExterior"] = lugar["num_exterior"]
    # `Colonia` es la clave numérica de c_Colonia (4 dígitos); un nombre escrito a mano
    # ("Centro") lo rechaza el SAT, así que solo se manda si es clave.
    colonia = str(lugar.get("colonia") or "").strip()
    if re.fullmatch(r"\d{4}", colonia):
        domicilio["Colonia"] = colonia
    if lugar.get("municipio_clave"):
        domicilio["Municipio"] = lugar["municipio_clave"]
    if lugar.get("localidad_clave"):
        domicilio["Localidad"] = lugar["localidad_clave"]
    return domicilio


def _ubicacion_cfdi(u: dict[str, Any]) -> dict[str, Any]:
    ubicacion: dict[str, Any] = {
        "TipoUbicacion": u["tipo"],  # "Origen" | "Destino"
        "RFCRemitenteDestinatario": u["lugar"]["rfc_remitente_destinatario"],
        "Domicilio": _domicilio(u["lugar"]),
    }
    if u["lugar"].get("nombre_remitente_destinatario"):
        ubicacion["NombreRemitenteDestinatario"] = u["lugar"]["nombre_remitente_destinatario"]
    if u.get("fecha_hora"):
        ubicacion["FechaHoraSalidaLlegada"] = u["fecha_hora"].strftime("%Y-%m-%dT%H:%M:%S")
    if u["tipo"] == "Destino" and u.get("distancia_km") is not None:
        ubicacion["DistanciaRecorrida"] = _num(u["distancia_km"])
    return ubicacion


def construir_items(concepto: dict[str, Any], montos: dict[str, Decimal], es_moral: bool) -> list[dict[str, Any]]:
    """`04-facturacion-cfdi §2-3` — un servicio = un concepto de flete."""
    taxes = [
        {
            "Name": "IVA",
            "Rate": "0.16",
            "Total": str(montos["iva_trasladado"]),
            "Base": str(montos["subtotal"]),
            "IsRetention": "false",
            "IsFederalTax": "true",
        }
    ]
    if es_moral:
        taxes.append(
            {
                "Name": "IVA RET",
                "Rate": "0.04",
                "Total": str(montos["iva_retenido"]),
                "Base": str(montos["subtotal"]),
                "IsRetention": "true",
                "IsFederalTax": "true",
            }
        )
    return [
        {
            "Quantity": "1",
            "ProductCode": concepto.get("clave_prod_serv", "78101802"),
            "UnitCode": concepto.get("clave_unidad", "SX"),
            "Unit": "Envío",
            "Description": concepto["descripcion"],
            "UnitPrice": str(montos["subtotal"]),
            "Subtotal": str(montos["subtotal"]),
            "TaxObject": "02",
            "Taxes": taxes,
            "Total": str(montos["total"]),
        }
    ]


def construir_carta_porte(
    ubicaciones: list[dict[str, Any]],
    mercancias: list[dict[str, Any]],
    autotransporte: dict[str, Any],
    figura: dict[str, Any],
    total_dist_rec: float,
) -> dict[str, Any]:
    """`04-facturacion-cfdi §4` — `Autotransporte` vive DENTRO de `Mercancias`."""
    peso_total = sum(m["peso_kg"] for m in mercancias)
    return {
        "TranspInternac": "No",
        "TotalDistRec": _num(total_dist_rec),
        "Ubicaciones": [_ubicacion_cfdi(u) for u in ubicaciones],
        "Mercancias": {
            "PesoBrutoTotal": _num(peso_total),
            "UnidadPeso": "KGM",
            "NumTotalMercancias": str(len(mercancias)),
            "Mercancia": [
                {
                    "BienesTransp": m["bienes_transp"],
                    "Descripcion": m["descripcion"],
                    "Cantidad": _num(m["cantidad"]),
                    "ClaveUnidad": m["clave_unidad"],
                    "Unidad": m.get("unidad_desc") or "Unidad",
                    "PesoEnKg": _num(m["peso_kg"]),
                    **({"MaterialPeligroso": "No"} if m.get("declarar_material_peligroso") else {}),
                }
                for m in mercancias
            ],
            "Autotransporte": {
                "PermSCT": autotransporte["perm_sct"],
                "NumPermisoSCT": autotransporte["num_permiso_sct"],
                "IdentificacionVehicular": {
                    "ConfigVehicular": autotransporte["config_vehicular"],
                    "PesoBrutoVehicular": str(autotransporte["peso_bruto_vehicular"]),
                    "PlacaVM": autotransporte["placa"],
                    **(
                        {"AnioModeloVM": str(autotransporte["anio_modelo"])}
                        if autotransporte.get("anio_modelo")
                        else {}
                    ),
                },
                "Seguros": {
                    "AseguraRespCivil": autotransporte.get("aseguradora") or "",
                    "PolizaRespCivil": autotransporte.get("poliza") or "",
                },
            },
        },
        "FiguraTransporte": [
            {
                "TipoFigura": "01",
                "RFCFigura": figura["rfc"],
                "NumLicencia": figura["num_licencia"],
                "NombreFigura": figura["nombre"],
            }
        ],
    }


def construir_payload_cfdi(
    *,
    serie: str,
    expedition_place: str,
    receptor: dict[str, Any],
    concepto: dict[str, Any],
    montos: dict[str, Decimal],
    ubicaciones: list[dict[str, Any]],
    mercancias: list[dict[str, Any]],
    autotransporte: dict[str, Any],
    figura: dict[str, Any],
    total_dist_rec: float,
) -> dict[str, Any]:
    """Payload completo de `POST /3/cfdis` (`04-facturacion-cfdi §1-4.5`).

    `expedition_place` es el CP de la sucursal del EMISOR (`EMISOR_LUGAR_EXPEDICION`),
    no del receptor -- confundirlos tira "El atributo 'ExpeditionPlace' debe existir
    como código postal en alguno de los Lugares de expedición en tu Perfil Fiscal".
    """
    es_moral = receptor["regimen_receptor"] == "moral"
    return {
        "Serie": serie,
        "CfdiType": "I",
        "PaymentForm": receptor.get("forma_pago", "99"),
        "ExpeditionPlace": expedition_place,
        "PaymentMethod": receptor["metodo_pago"],
        "Currency": "MXN",
        "Exportation": "01",
        "Receiver": {
            "Name": receptor["razon_social"],
            "CfdiUse": receptor["uso_cfdi"],
            "Rfc": receptor["rfc"],
            "FiscalRegime": receptor["regimen_fiscal"],
            "TaxZipCode": receptor["cp_fiscal"],
        },
        "Items": construir_items(concepto, montos, es_moral),
        "Complemento": {
            "CartaPorte31": construir_carta_porte(
                ubicaciones, mercancias, autotransporte, figura, total_dist_rec
            )
        },
    }
