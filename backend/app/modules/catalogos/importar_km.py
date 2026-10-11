"""Importa los km por destino del Excel de Carta Porte (una hoja por cliente).

Cada hoja de cliente lista sus destinos: nombre en A, RFC en B, CP en C y km en D
("83km", "55Km", 180, o vacío). Se empata con los lugares del cliente por nombre
(y CP si hay homónimos) y se guarda `lugar.distancia_km` + `km_confirmado`. Las filas sin
km no se tocan: esos destinos siguen con la sugerencia de 70 km "no confirmado".
El Excel es privado (`.misc/`), por eso se sube desde la app en vez de ir en el repo.
"""
import io
import re
import unicodedata

import openpyxl
from sqlmodel import Session, select

from app.core.errors import AppError
from app.modules.catalogos.models import Cliente, Lugar

_FILAS_QUE_NO_SON_DESTINO = {
    "NOMBRE", "PAQUETERIA", "GENERAL", "SAVEIRO", "NISSAN ROJA", "NISSAN BLANCA", "FORD 350",
    "FORD 450", "RABON", "GERMAN", "DANIEL", "ISRAEL", "FELIPE", "ENRIQUE", "PLANTILLA",
}
_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def _norm(texto: object) -> str:
    s = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _cp(v: object) -> str | None:
    texto = str(v).replace("﻿", "").strip().removesuffix(".0") if v is not None else ""
    return texto.zfill(5) if texto.isdigit() and 4 <= len(texto) <= 5 else None


def _km(v: object) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    m = _NUMERO.search(str(v))
    if not m:
        return None
    km = float(m.group().replace(",", "."))
    return km if km > 0 else None


def _cliente_de_hoja(hoja: str, clientes: list[Cliente]) -> Cliente | None:
    clave = _norm(hoja)
    if not clave:
        return None
    for c in clientes:
        for nombre in (c.nombre_comercial, c.razon_social):
            n = _norm(nombre)
            if n and (clave in n or n in clave):
                return c
    return None


def importar_km(session: Session, contenido: bytes) -> dict:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001 — cualquier archivo que no sea un .xlsx válido
        raise AppError("validation_error", "No se pudo leer el archivo: sube el .xlsx de Carta Porte", 422) from exc

    clientes = list(session.exec(select(Cliente)).all())
    resumen: list[dict] = []
    sin_cliente: list[str] = []
    for ws in wb.worksheets:
        cliente = _cliente_de_hoja(ws.title, clientes)
        if cliente is None:
            sin_cliente.append(ws.title)
            continue
        lugares: dict[str, list[Lugar]] = {}
        for l in session.exec(select(Lugar).where(Lugar.cliente_id == cliente.id)).all():
            lugares.setdefault(_norm(l.nombre), []).append(l)

        actualizados = sin_km = 0
        sin_lugar: list[str] = []
        vistos: set[tuple[str, str]] = set()
        for fila in ws.iter_rows(min_row=2, values_only=True):
            nombre = str(fila[0]).replace("﻿", "").strip() if fila and fila[0] is not None else ""
            cp = _cp(fila[2] if len(fila) > 2 else None)
            if not nombre or nombre.upper() in _FILAS_QUE_NO_SON_DESTINO or cp is None:
                continue
            if (nombre, cp) in vistos:
                continue
            vistos.add((nombre, cp))
            km = _km(fila[3] if len(fila) > 3 else None)
            candidatos = lugares.get(_norm(nombre), [])
            lugar = next((l for l in candidatos if l.codigo_postal == cp), candidatos[0] if candidatos else None)
            if lugar is None:
                sin_lugar.append(nombre)
            elif km is None:
                sin_km += 1
            else:
                lugar.distancia_km = km
                lugar.km_confirmado = True
                session.add(lugar)
                actualizados += 1
        resumen.append(
            {
                "hoja": ws.title,
                "cliente": cliente.nombre_comercial,
                "actualizados": actualizados,
                "sin_km": sin_km,
                "sin_lugar": sin_lugar,
            }
        )
    session.commit()
    return {"hojas": resumen, "hojas_sin_cliente": sin_cliente}
