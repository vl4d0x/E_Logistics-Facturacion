"""Lectura del Excel de registros de Vlad y escritura del número de factura de vuelta.

- Lectura: openpyxl en modo solo lectura (valores ya calculados de las fórmulas).
- Escritura: NO se usa openpyxl para guardar, porque al re-guardar pierde dibujos,
  comentarios y otras partes del libro. Se edita directamente el XML de la hoja dentro
  del .xlsx (es un zip): solo las celdas de la columna FACTURA de las filas facturadas;
  el resto de los archivos del libro se copian byte por byte.
"""
from __future__ import annotations

import io
import posixpath
import re
import zipfile
from datetime import date, datetime
from xml.sax.saxutils import escape

import openpyxl

from app.core.errors import AppError
from app.modules.registro_excel.matching import normalizar

# Encabezado normalizado → campo. El orden de columnas del Excel no importa.
COLUMNAS = {
    "FECHA": "fecha",
    "CLIENTE": "cliente",
    "PROP": "propietario",
    "OPERADOR": "operador",
    "UNIDAD": "unidad",
    "ORIGEN": "origen",
    "DESTINO": "destino",
    "SUBTOTAL": "subtotal",
    "IVA RET": "iva",
    "IVA": "iva",
    "TOTAL": "total",
    "FACTURA": "factura",
    "REF": "ref",
    "DINORA MENDOZA": "notas",
    "NOTAS": "notas",
    "ESTATUS PAGO": "estatus_pago",
    "KILOMETROS": "km",
}
REQUERIDAS = {"fecha", "cliente", "destino", "factura"}


def _err(msg: str) -> AppError:
    return AppError("validation_error", msg, 422, details=[{"field": "file", "issue": msg}])


def _letra(col: int) -> str:
    s = ""
    while col:
        col, r = divmod(col - 1, 26)
        s = chr(65 + r) + s
    return s


def _indice_columna(letras: str) -> int:
    n = 0
    for ch in letras:
        n = n * 26 + (ord(ch) - 64)
    return n


def _valor(v: object) -> object:
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        v = v.replace("﻿", "").strip()
        return v or None
    return v


def leer_registros(contenido: bytes) -> tuple[str, dict[str, str], list[tuple[int, dict]]]:
    """Devuelve (hoja, {campo: letra de columna}, [(fila, datos)]) de la hoja de registros:
    la primera cuyo encabezado (fila 1) trae FECHA, CLIENTE, DESTINO y FACTURA."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as exc:
        raise _err("El archivo no es un Excel (.xlsx) válido") from exc
    try:
        for ws in wb.worksheets:
            filas = ws.iter_rows(values_only=True)
            encabezado = next(filas, None)
            if not encabezado:
                continue
            columnas: dict[str, int] = {}
            for i, h in enumerate(encabezado):
                campo = COLUMNAS.get(normalizar(h))
                if campo and campo not in columnas:
                    columnas[campo] = i
            if not REQUERIDAS <= columnas.keys():
                continue
            registros: list[tuple[int, dict]] = []
            for n, fila in enumerate(filas, start=2):
                datos = {
                    campo: _valor(fila[i]) if i < len(fila) else None for campo, i in columnas.items()
                }
                if datos.get("cliente") is None and datos.get("destino") is None:
                    continue
                registros.append((n, datos))
            letras = {campo: _letra(i + 1) for campo, i in columnas.items()}
            return ws.title, letras, registros
    finally:
        wb.close()
    raise _err("No encontré la hoja de registros (encabezados FECHA, CLIENTE, DESTINO y FACTURA)")


# --- Escritura de la columna FACTURA ------------------------------------------------

def _ruta_hoja(z: zipfile.ZipFile, hoja: str) -> str:
    workbook = z.read("xl/workbook.xml").decode("utf-8")
    rid = None
    for m in re.finditer(r"<sheet\b[^>]*>", workbook):
        tag = m.group(0)
        nombre = re.search(r'\bname="([^"]*)"', tag)
        if nombre and nombre.group(1) == escape(hoja, {'"': "&quot;"}):
            rid = re.search(r'\br:id="([^"]*)"', tag) or re.search(r'\bid="([^"]*)"', tag)
            break
    if rid is None:
        raise _err(f"El Excel ya no tiene la hoja {hoja}")
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    for m in re.finditer(r"<Relationship\b[^>]*>", rels):
        tag = m.group(0)
        if f'Id="{rid.group(1)}"' in tag:
            target = re.search(r'Target="([^"]*)"', tag).group(1)
            return target.lstrip("/") if target.startswith("/") else posixpath.normpath(f"xl/{target}")
    raise _err(f"No encontré los datos de la hoja {hoja}")


def _celda_xml(ref: str, valor: str, atributos: str) -> str:
    atributos = re.sub(r'\s+t="[^"]*"', "", atributos)
    if re.fullmatch(r"\d{1,15}", valor):
        return f'<c r="{ref}"{atributos}><v>{valor}</v></c>'
    return f'<c r="{ref}"{atributos} t="inlineStr"><is><t>{escape(valor)}</t></is></c>'


def _poner_en_fila(fila_xml: str, ref: str, columna: int, valor: str) -> tuple[str, bool]:
    """Pone el valor en la celda `ref` de la fila. No sobrescribe una celda con dato."""
    patron = re.compile(r'<c r="' + ref + r'"((?:\s[^>]*?)?)(/>|>(.*?)</c>)', re.DOTALL)
    m = patron.search(fila_xml)
    if m:
        contenido = m.group(3) or ""
        if "<v>" in contenido or "<is>" in contenido or "<f" in contenido:
            return fila_xml, False
        return fila_xml[: m.start()] + _celda_xml(ref, valor, m.group(1)) + fila_xml[m.end():], True
    # Sin celda: se inserta respetando el orden de columnas.
    for c in re.finditer(r'<c r="([A-Z]+)\d+"', fila_xml):
        if _indice_columna(c.group(1)) > columna:
            return fila_xml[: c.start()] + _celda_xml(ref, valor, "") + fila_xml[c.start():], True
    cierre = fila_xml.rfind("</row>")
    if cierre == -1:  # <row .../> vacía
        fila_xml = fila_xml[:-2] + ">" + "</row>"
        cierre = fila_xml.rfind("</row>")
    return fila_xml[:cierre] + _celda_xml(ref, valor, "") + fila_xml[cierre:], True


def escribir_columna(contenido: bytes, hoja: str, letra: str, valores: dict[int, str]) -> tuple[bytes, list[int]]:
    """Copia del Excel con `valores` ({fila: texto}) en la columna `letra` de `hoja`.
    Devuelve (bytes, filas escritas). Las celdas que ya tienen algo no se tocan."""
    escritas: list[int] = []
    origen = zipfile.ZipFile(io.BytesIO(contenido))
    ruta = _ruta_hoja(origen, hoja)
    xml = origen.read(ruta).decode("utf-8")
    columna = _indice_columna(letra)
    partes: list[str] = []
    ultimo = 0
    pendientes = {f: str(v).strip() for f, v in valores.items() if v is not None and str(v).strip()}
    if pendientes:
        for m in re.finditer(r'<row r="(\d+)"[^>]*?(?:/>|>.*?</row>)', xml, re.DOTALL):
            fila = int(m.group(1))
            if fila not in pendientes:
                continue
            nuevo, ok = _poner_en_fila(m.group(0), f"{letra}{fila}", columna, pendientes[fila])
            if ok:
                partes.append(xml[ultimo: m.start()])
                partes.append(nuevo)
                ultimo = m.end()
                escritas.append(fila)
    partes.append(xml[ultimo:])
    nuevo_xml = "".join(partes)

    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as destino:
        for info in origen.infolist():
            datos = nuevo_xml.encode("utf-8") if info.filename == ruta else origen.read(info.filename)
            destino.writestr(info, datos, compress_type=info.compress_type)
    return salida.getvalue(), escritas
