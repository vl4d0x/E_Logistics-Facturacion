"""Extrae los lugares frecuentes (empresas destino) del Excel de Vlad a un YAML privado.

Lee `DatosCartaPorte.xlsx` (hojas de cliente), resuelve estado y claves de
municipio/localidad por CP con el catálogo de Facturama (no se inventa nada) y escribe
`lugares-fase1.yaml` junto al Excel. Ambos archivos son privados (`.misc/`, gitignored).

Uso:
    cd backend && python -m scripts.extraer_lugares ../.misc/DatosCartaPorte.xlsx CHEMITAL AERZEN ...
"""
import re
import sys
from pathlib import Path

import openpyxl
import yaml

from app.integrations.facturama import FacturamaClient

_RFC = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
_FILAS_QUE_NO_SON_DESTINO = {
    "NOMBRE", "PAQUETERIA", "GENERAL", "SAVEIRO", "NISSAN ROJA", "NISSAN BLANCA", "FORD 350",
    "FORD 450", "RABON", "GERMAN", "DANIEL", "ISRAEL", "FELIPE", "ENRIQUE", "PLANTILLA",
}


def _limpio(v) -> str:
    return str(v).replace("﻿", "").strip() if v is not None else ""


def _cp(v) -> str | None:
    texto = _limpio(v)
    texto = texto.removesuffix(".0")
    return texto.zfill(5) if texto.isdigit() and 4 <= len(texto) <= 5 else None


def filas_destino(ws) -> list[dict]:
    """Filas con nombre en A, CP válido en C (los vehículos/operadores no lo tienen)."""
    vistos: set[tuple[str, str]] = set()
    lugares = []
    for fila in ws.iter_rows(min_row=2, values_only=True):
        nombre = _limpio(fila[0])
        cp = _cp(fila[2] if len(fila) > 2 else None)
        if not nombre or nombre.upper() in _FILAS_QUE_NO_SON_DESTINO or cp is None:
            continue
        if (nombre, cp) in vistos:
            continue
        vistos.add((nombre, cp))
        rfc = _limpio(fila[1]).upper()
        lugares.append(
            {
                "nombre": nombre,
                "rfc": rfc if _RFC.match(rfc) else None,
                "codigo_postal": cp,
                "referencia": _limpio(fila[4]) or None if len(fila) > 4 and isinstance(fila[4], str) else None,
            }
        )
    return lugares


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    ruta = Path(sys.argv[1])
    wb = openpyxl.load_workbook(ruta, data_only=True)
    salida: dict[str, list[dict]] = {}
    with FacturamaClient() as facturama:
        cache: dict[str, dict | None] = {}
        for hoja in sys.argv[2:]:
            lugares = filas_destino(wb[hoja])
            for lugar in lugares:
                cp = lugar["codigo_postal"]
                if cp not in cache:
                    cache[cp] = facturama.resolve_postal_code(cp)
                r = cache[cp] or {}
                lugar["estado"] = r.get("StateCode")
                lugar["municipio_clave"] = r.get("MunicipalityCode") or None
                lugar["localidad_clave"] = r.get("LocationCode") or None
                if not lugar["estado"] or not lugar["municipio_clave"]:
                    lugar["REVISAR"] = "CP no resuelto por completo en el catálogo SAT; confirmar el CP"
            salida[hoja] = lugares
            print(f"{hoja}: {len(lugares)} lugares ({sum('REVISAR' in l for l in lugares)} por revisar)")
    destino = ruta.parent / "lugares-fase1.yaml"
    destino.write_text(yaml.safe_dump(salida, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print("escrito", destino)


if __name__ == "__main__":
    main()
