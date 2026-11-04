"""factura: importadas del Facturador Electrónico (sin servicio), cliente_id, origen, pagado externo

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("factura", sa.Column("cliente_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_factura_cliente", "factura", "cliente", ["cliente_id"], ["id"])
    op.create_index("ix_factura_cliente_id", "factura", ["cliente_id"])
    op.add_column("factura", sa.Column("origen", sa.String(), nullable=False, server_default="app"))
    op.create_index("ix_factura_origen", "factura", ["origen"])
    op.add_column("factura", sa.Column("pagado_externo", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("factura", sa.Column("parcialidades_externas", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("factura", sa.Column("receptor_nombre", sa.String(), nullable=True))
    op.execute("UPDATE factura SET cliente_id = servicio.cliente_id FROM servicio WHERE servicio.id = factura.servicio_id")
    op.alter_column("factura", "servicio_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM factura WHERE servicio_id IS NULL")
    op.alter_column("factura", "servicio_id", existing_type=sa.Uuid(), nullable=False)
    for col in ("receptor_nombre", "parcialidades_externas", "pagado_externo"):
        op.drop_column("factura", col)
    op.drop_index("ix_factura_origen", table_name="factura")
    op.drop_column("factura", "origen")
    op.drop_index("ix_factura_cliente_id", table_name="factura")
    op.drop_constraint("fk_factura_cliente", "factura", type_="foreignkey")
    op.drop_column("factura", "cliente_id")
