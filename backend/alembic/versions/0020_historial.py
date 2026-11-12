"""movimiento: historial de lo que hace cada admin (facturar, enviar, cancelar)

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "movimiento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("servicio_id", sa.Uuid(), nullable=True),
        sa.Column("factura_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    )
    op.create_index("ix_movimiento_usuario_id", "movimiento", ["usuario_id"])
    op.create_index("ix_movimiento_tipo", "movimiento", ["tipo"])
    op.create_index("ix_movimiento_created_at", "movimiento", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_movimiento_created_at", table_name="movimiento")
    op.drop_index("ix_movimiento_tipo", table_name="movimiento")
    op.drop_index("ix_movimiento_usuario_id", table_name="movimiento")
    op.drop_table("movimiento")
