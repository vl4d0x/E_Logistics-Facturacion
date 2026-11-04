"""foto_evidencia: fotos opcionales del servicio que se adjuntan al correo de la factura

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "foto_evidencia",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("servicio_id", sa.Uuid(), sa.ForeignKey("servicio.id", ondelete="CASCADE"), nullable=False),
        sa.Column("archivo_key", sa.String(), nullable=False),
        sa.Column("mime", sa.String(), nullable=False),
        sa.Column("nombre_original", sa.String(), nullable=True),
        sa.Column("subido_por", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("subido_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    )
    op.create_index("ix_foto_evidencia_servicio_id", "foto_evidencia", ["servicio_id"])


def downgrade() -> None:
    op.drop_index("ix_foto_evidencia_servicio_id", table_name="foto_evidencia")
    op.drop_table("foto_evidencia")
