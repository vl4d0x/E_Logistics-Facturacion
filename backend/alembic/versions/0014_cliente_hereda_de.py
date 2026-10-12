"""cliente.hereda_de_id: otra razón social que usa los lugares y mercancías de un cliente

AERZEN RENTAL MEXICO (ARM231214NK0) hereda de AERZEN MEXICO (AME081219M12): a veces piden
facturar a la otra razón social, pero los lugares y mercancías son los mismos. También quita
los espacios sobrantes en los nombres de los clientes ("AERZEN " → "AERZEN").

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cliente", sa.Column("hereda_de_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_cliente_hereda_de", "cliente", "cliente", ["hereda_de_id"], ["id"])
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE cliente SET nombre_comercial = TRIM(nombre_comercial), razon_social = TRIM(razon_social)"))
    conn.execute(
        sa.text(
            "UPDATE cliente SET hereda_de_id = (SELECT id FROM cliente WHERE rfc = 'AME081219M12' LIMIT 1) "
            "WHERE rfc = 'ARM231214NK0' AND hereda_de_id IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_cliente_hereda_de", "cliente", type_="foreignkey")
    op.drop_column("cliente", "hereda_de_id")
