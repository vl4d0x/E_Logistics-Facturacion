"""desglose de precio por destino (viaje.monto_desglose) y texto del correo por cliente
(cliente.plantilla_correo), con los textos que dio Vlad para cada cliente

Los clientes sin plantilla (Parautos y los demás) usan el texto general del código.
Las plantillas se pueden editar después en Catálogos > Clientes.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-11

"""
import re
import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Clave = texto que aparece en el nombre comercial o la razón social del cliente.
_PLANTILLAS = {
    "AERZEN": (
        "Lic. Erika / Lic. Rosario\n\n"
        "Le envío la factura #{folio} correspondiente al servicio realizado el día {dia} de {mes} del {anio}."
    ),
    "CHEMITAL": "{operador} {unidad} {origen} -> {destinos}",
    "FARMABIOT": "Hola!\n\nComparto la factura y carta porte del servicio del día de hoy\n\nSaludos",
    "LESAFFRE": "Le envío la factura #{folio} correspondiente al servicio realizado el día {dia} de {mes} del {anio}.",
}


def _norm(texto: object) -> str:
    s = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def upgrade() -> None:
    op.add_column("viaje", sa.Column("monto_desglose", sa.Numeric(12, 2), nullable=True))
    op.add_column("cliente", sa.Column("plantilla_correo", sa.String(), nullable=True))

    conn = op.get_bind()
    clientes = conn.execute(sa.text("SELECT id, nombre_comercial, razon_social FROM cliente")).fetchall()
    for c in clientes:
        nombres = _norm(c.nombre_comercial) + " " + _norm(c.razon_social)
        for clave, plantilla in _PLANTILLAS.items():
            if clave in nombres:
                conn.execute(
                    sa.text("UPDATE cliente SET plantilla_correo = :p WHERE id = :id"),
                    {"p": plantilla, "id": c.id},
                )
                break


def downgrade() -> None:
    op.drop_column("cliente", "plantilla_correo")
    op.drop_column("viaje", "monto_desglose")
