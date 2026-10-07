"""Siembra los catálogos de Fase 1 desde los YAML privados (`.misc/`, gitignored).

Idempotente: cada registro se busca por su llave natural (placa, RFC, cliente+nombre) y
se actualiza si existe, se crea si no. No borra nada. Los datos reales NO viven en el repo.

Uso:
    cd backend && python -m scripts.seed_catalogos [--dry-run] \
        [../.misc/catalogos-fase1.yaml] [../.misc/lugares-fase1.yaml]

Apunta a la base de `DATABASE_URL` del entorno: revisa a cuál antes de correrlo.
"""
import sys
from pathlib import Path

import yaml
from sqlmodel import Session, select

from app.core.db import engine
from app.modules.catalogos.models import (
    Cliente,
    Lugar,
    MercanciaFrecuente,
    Operador,
    Unidad,
)


def _upsert(session: Session, modelo, filtro: dict, valores: dict, contador: dict) -> object:
    stmt = select(modelo)
    for campo, valor in filtro.items():
        stmt = stmt.where(getattr(modelo, campo) == valor)
    fila = session.exec(stmt).first()
    if fila is None:
        fila = modelo(**filtro, **valores)
        contador["creados"] += 1
    else:
        for campo, valor in valores.items():
            setattr(fila, campo, valor)
        contador["actualizados"] += 1
    session.add(fila)
    session.flush()
    return fila


def sembrar(session: Session, catalogos: dict, lugares: dict) -> dict[str, dict]:
    permisos = {k: v for k, v in catalogos["emisor"]["permisos_sct"].items()}
    resumen: dict[str, dict] = {}

    def cont(nombre: str) -> dict:
        return resumen.setdefault(nombre, {"creados": 0, "actualizados": 0})

    for u in catalogos["unidades"]:
        permiso = permisos[u["perm_sct"].lower()]
        _upsert(
            session, Unidad, {"placa": u["placa"]},
            {
                "apodo": u["apodo"],
                "anio_modelo": u["anio_modelo"],
                "config_vehicular": u["config_vehicular"],
                "peso_bruto_vehicular": u["peso_bruto_vehicular_ton"],
                "capacidad_carga_kg": u.get("capacidad_carga_kg"),
                "perm_sct": permiso["clave_tipo_permiso"],
                "num_permiso_sct": permiso["numero"],
                "aseguradora_resp_civil": u["aseguradora_resp_civil"],
                "poliza_resp_civil": u["poliza_resp_civil"],
                "tipo_medidor": u.get("tipo_medidor", "aguja"),
                "num_barras": u.get("num_barras"),
                "capacidad_tanque_l": u.get("capacidad_tanque_l"),
            },
            cont("unidades"),
        )

    for o in catalogos["operadores"]:
        # Sin licencia real se siembra vacía a propósito: la validación pre-timbrado
        # (`validar.py`, "operador_completo") bloquea facturar con ese operador.
        _upsert(
            session, Operador, {"rfc": o["rfc"]},
            {"nombre": o["nombre_completo"], "num_licencia": o["num_licencia"] or ""},
            cont("operadores"),
        )

    for c in catalogos["clientes_activos"]:
        cliente = _upsert(
            session, Cliente, {"rfc": c["rfc"]},
            {
                "razon_social": c["razon_social"],
                "nombre_comercial": c["nombre_comercial"],
                "cp_fiscal": c["cp_fiscal"],
                "regimen_fiscal": c["regimen_fiscal"],
                "regimen_receptor": c["regimen_receptor"],
                "uso_cfdi": c["uso_cfdi"],
                "metodo_pago_default": c["metodo_pago_default"],
                "modo_acuse": c["modo_acuse"],
                "emails_facturacion": c["emails_facturacion"],
                "dias_credito": 30,
                "requiere_folio_concepto": c["clave_temporal"] == "CHEMITAL",
            },
            cont("clientes"),
        )
        for m in c.get("mercancias_frecuentes") or []:
            if c["clave_temporal"] == "FARMABIOT":
                continue  # catálogo de medicinas en pausa por instrucción de Vlad (2026-10-06)
            _upsert(
                session, MercanciaFrecuente,
                {"cliente_id": cliente.id, "nombre_humano": m["nombre_humano"]},
                {
                    "bienes_transp": m["bienes_transp"],
                    "clave_unidad": m["clave_unidad"],
                    "unidad_desc": m["unidad_desc"],
                },
                cont("mercancias"),
            )
        for l in lugares.get(c["clave_temporal"], []):
            if not l.get("estado"):
                continue
            _upsert(
                session, Lugar,
                {"cliente_id": cliente.id, "nombre": l["nombre"], "codigo_postal": l["codigo_postal"]},
                {
                    "rfc_remitente_destinatario": l["rfc"] or "XAXX010101000",
                    "nombre_remitente_destinatario": l["nombre"],
                    "estado": l["estado"],
                    "municipio_clave": l.get("municipio_clave"),
                    "localidad_clave": l.get("localidad_clave"),
                    "referencia": l.get("referencia"),
                    # La planta del cliente (mismo nombre que su razón social) es el origen habitual.
                    "es_origen_predeterminado": l["nombre"] == c["razon_social"],
                },
                cont("lugares"),
            )
    return resumen


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    ruta_cat = Path(args[0] if args else "../.misc/catalogos-fase1.yaml")
    ruta_lug = Path(args[1] if len(args) > 1 else ruta_cat.parent / "lugares-fase1.yaml")
    catalogos = yaml.safe_load(ruta_cat.read_text(encoding="utf-8"))
    lugares = yaml.safe_load(ruta_lug.read_text(encoding="utf-8"))

    print("Base de datos destino:", engine.url.render_as_string(hide_password=True))
    with Session(engine) as session:
        resumen = sembrar(session, catalogos, lugares)
        if dry:
            session.rollback()
            print("--dry-run: nada se guardó")
        else:
            session.commit()
    for tabla, c in resumen.items():
        print(f"  {tabla}: {c['creados']} creados, {c['actualizados']} actualizados")


if __name__ == "__main__":
    main()
