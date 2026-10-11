"""carga los km por destino del Excel de Carta Porte en `lugar`

Datos en `alembic/data/km_lugares.json` (hoja = cliente; nombre, cp, km). Solo llena
lugares del cliente con ese nombre que aún no tengan km confirmado; los destinos sin km
en el Excel no se tocan (el sugeridor usa 70 km "no confirmado"). Los km se pueden
corregir a mano en Catálogos > Lugares.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-11

"""
import json
import re
import unicodedata
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DATOS = Path(__file__).resolve().parent.parent / "data" / "km_lugares.json"


def _norm(texto: object) -> str:
    s = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _cliente_de_hoja(hoja: str, clientes: list) -> object | None:
    clave = _norm(hoja)
    if not clave:
        return None
    for c in clientes:
        for nombre in (c.nombre_comercial, c.razon_social):
            n = _norm(nombre)
            if n and (clave in n or n in clave):
                return c
    return None


def upgrade() -> None:
    if not _DATOS.exists():
        return
    datos = json.loads(_DATOS.read_text(encoding="utf-8-sig"))
    bind = op.get_bind()
    clientes = list(bind.execute(sa.text("SELECT id, nombre_comercial, razon_social FROM cliente")))
    for hoja, filas in datos.items():
        cliente = _cliente_de_hoja(hoja, clientes)
        if cliente is None or not filas:
            continue
        lugares = bind.execute(
            sa.text("SELECT id, nombre, codigo_postal FROM lugar WHERE cliente_id = :c AND km_confirmado = false"),
            {"c": cliente.id},
        ).all()
        por_nombre: dict[str, list] = {}
        for l in lugares:
            por_nombre.setdefault(_norm(l.nombre), []).append(l)
        for fila in filas:
            if fila.get("km") is None:
                continue
            candidatos = por_nombre.get(_norm(fila["nombre"]), [])
            lugar = next((l for l in candidatos if l.codigo_postal == fila["cp"]), candidatos[0] if candidatos else None)
            if lugar is None:
                continue
            bind.execute(
                sa.text("UPDATE lugar SET distancia_km = :km, km_confirmado = true WHERE id = :id"),
                {"km": float(fila["km"]), "id": lugar.id},
            )


def downgrade() -> None:
    pass  # los km quedan; son datos, no estructura
