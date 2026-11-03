"""Facturar con el Excel de registros: archivo vigente, filas, servicio por fila, alias;
viaje.sin_acuse (el destino no tiene REF ni escaneo)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column(
        "viaje", sa.Column("sin_acuse", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_table(
        "registro_excel",
        *_ts(),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nombre_archivo", sa.String(), nullable=False),
        sa.Column("hoja", sa.String(), nullable=False),
        sa.Column("columnas", sa.JSON(), nullable=False),
        sa.Column("contenido", sa.LargeBinary(), nullable=False),
        sa.Column("total_filas", sa.Integer(), nullable=False),
        sa.Column("ultima_fila", sa.Integer(), nullable=False),
        sa.Column("subido_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("subido_por", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=True),
    )
    op.create_table(
        "registro_excel_fila",
        *_ts(),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("registro_id", sa.Uuid(), sa.ForeignKey("registro_excel.id"), nullable=False),
        sa.Column("fila", sa.Integer(), nullable=False),
        sa.Column("datos", sa.JSON(), nullable=False),
        sa.UniqueConstraint("registro_id", "fila", name="uq_registro_excel_fila"),
    )
    op.create_index("ix_registro_excel_fila_registro_id", "registro_excel_fila", ["registro_id"])
    op.create_index("ix_registro_excel_fila_fila", "registro_excel_fila", ["fila"])
    op.create_table(
        "registro_excel_servicio",
        *_ts(),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("servicio_id", sa.Uuid(), sa.ForeignKey("servicio.id"), nullable=False, unique=True),
        sa.Column("fila", sa.Integer(), nullable=False),
        sa.Column("huella", sa.String(), nullable=False),
    )
    op.create_index("ix_registro_excel_servicio_fila", "registro_excel_servicio", ["fila"])
    op.create_table(
        "registro_excel_alias",
        *_ts(),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), sa.ForeignKey("cliente.id"), nullable=True),
        sa.Column("texto", sa.String(), nullable=False),
        sa.Column("objetivo_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("tipo", "cliente_id", "texto", name="uq_registro_excel_alias"),
    )


def downgrade() -> None:
    op.drop_table("registro_excel_alias")
    op.drop_index("ix_registro_excel_servicio_fila", table_name="registro_excel_servicio")
    op.drop_table("registro_excel_servicio")
    op.drop_index("ix_registro_excel_fila_fila", table_name="registro_excel_fila")
    op.drop_index("ix_registro_excel_fila_registro_id", table_name="registro_excel_fila")
    op.drop_table("registro_excel_fila")
    op.drop_table("registro_excel")
    op.drop_column("viaje", "sin_acuse")
