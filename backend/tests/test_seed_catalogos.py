"""`scripts/seed_catalogos.py` — idempotencia y reglas, con datos sintéticos (no los reales)."""
from sqlmodel import Session, select

from app.modules.catalogos.models import Lugar, MercanciaFrecuente, Operador, Unidad
from scripts.seed_catalogos import sembrar

CATALOGOS = {
    "emisor": {
        "permisos_sct": {
            "paqueteria": {"numero": "P-1", "clave_tipo_permiso": "TPAF14"},
            "general": {"numero": "G-1", "clave_tipo_permiso": "TPAF01"},
        }
    },
    "unidades": [
        {
            "apodo": "UNIDAD X", "placa": "AAA111", "anio_modelo": 2019, "config_vehicular": "VL",
            "peso_bruto_vehicular_ton": 0.5, "capacidad_carga_kg": 500, "perm_sct": "PAQUETERIA",
            "aseguradora_resp_civil": "SURA", "poliza_resp_civil": "1-1", "tipo_medidor": "barras",
            "num_barras": 8,
        }
    ],
    "operadores": [
        {"nombre_completo": "CON LICENCIA", "rfc": "AAAA010101AAA", "num_licencia": "L1"},
        {"nombre_completo": "SIN LICENCIA", "rfc": "BBBB010101BBB", "num_licencia": None},
    ],
    "clientes_activos": [
        {
            "clave_temporal": "CHEMITAL", "razon_social": "CHEMITAL DE MEXICO",
            "nombre_comercial": "CHEMITAL DE MEXICO", "rfc": "CME091007LG1", "cp_fiscal": "52004",
            "regimen_fiscal": "601", "regimen_receptor": "moral", "uso_cfdi": "G03",
            "metodo_pago_default": "PPD", "modo_acuse": "referencia", "emails_facturacion": ["a@x.mx"],
            "mercancias_frecuentes": [
                {"nombre_humano": "Cosa", "bienes_transp": "12164501", "clave_unidad": "X4G", "unidad_desc": "Caja"}
            ],
        },
        {
            "clave_temporal": "FARMABIOT", "razon_social": "FARMABIOT", "nombre_comercial": "FARMABIOT",
            "rfc": "FAR9702117V4", "cp_fiscal": "50200", "regimen_fiscal": "601", "regimen_receptor": "moral",
            "uso_cfdi": "G03", "metodo_pago_default": "PPD", "modo_acuse": "escaneo",
            "emails_facturacion": [], "mercancias_frecuentes": [
                {"nombre_humano": "Medicina", "bienes_transp": "51111617", "clave_unidad": "H87", "unidad_desc": None}
            ],
        },
    ],
}
LUGARES = {
    "CHEMITAL": [
        {"nombre": "CHEMITAL DE MEXICO", "rfc": "CME091007LG1", "codigo_postal": "52004", "estado": "MEX",
         "municipio_clave": "051", "localidad_clave": None, "referencia": None},
        {"nombre": "DESTINO SIN RFC", "rfc": None, "codigo_postal": "06600", "estado": "CMX",
         "municipio_clave": "015", "localidad_clave": "06", "referencia": "CDMX"},
        {"nombre": "CP NO RESUELTO", "rfc": None, "codigo_postal": "99999", "estado": None,
         "municipio_clave": None, "localidad_clave": None, "referencia": None},
    ]
}


def test_siembra_es_idempotente_y_respeta_las_reglas(session: Session):
    primera = sembrar(session, CATALOGOS, LUGARES)
    segunda = sembrar(session, CATALOGOS, LUGARES)
    session.commit()

    assert primera["lugares"] == {"creados": 2, "actualizados": 0}  # el CP sin estado se omite
    assert segunda["lugares"] == {"creados": 0, "actualizados": 2}
    assert len(session.exec(select(Unidad)).all()) == 1

    unidad = session.exec(select(Unidad)).one()
    assert unidad.perm_sct == "TPAF14" and unidad.num_permiso_sct == "P-1"

    sin_licencia = session.exec(select(Operador).where(Operador.rfc == "BBBB010101BBB")).one()
    assert sin_licencia.num_licencia == ""  # vacía a propósito: bloquea facturar con él

    origen = session.exec(select(Lugar).where(Lugar.es_origen_predeterminado)).all()
    assert [l.nombre for l in origen] == ["CHEMITAL DE MEXICO"]
    sin_rfc = session.exec(select(Lugar).where(Lugar.nombre == "DESTINO SIN RFC")).one()
    assert sin_rfc.rfc_remitente_destinatario == "XAXX010101000"

    # Farmabiot (catálogo en pausa) no recibe mercancías
    nombres = [m.nombre_humano for m in session.exec(select(MercanciaFrecuente)).all()]
    assert nombres == ["Cosa"]
