"""fase 3 — operación en campo (inspeccion_salida, reporte_cierre, carga_combustible)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inspeccion_salida",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("servicio_id", sa.Uuid(), nullable=False),
        sa.Column("operador_id", sa.Uuid(), nullable=False),
        sa.Column("unidad_id", sa.Uuid(), nullable=False),
        sa.Column("unidad_limpia", sa.Boolean(), nullable=False),
        sa.Column("fumigacion_vigente", sa.Boolean(), nullable=False),
        sa.Column("botiquin", sa.Boolean(), nullable=False),
        sa.Column("casco_chaleco", sa.Boolean(), nullable=False),
        sa.Column("aceite_ok", sa.Boolean(), nullable=False),
        sa.Column("anticongelante_ok", sa.Boolean(), nullable=False),
        sa.Column("neumaticos_ok", sa.Boolean(), nullable=False),
        sa.Column("extintor_ok", sa.Boolean(), nullable=False),
        sa.Column("todo_ok", sa.Boolean(), nullable=False),
        sa.Column("observaciones", sa.String(), nullable=True),
        sa.Column("nivel_combustible", sa.Numeric(), nullable=False),
        sa.Column("lectura_medidor", sa.JSON(), nullable=False),
        sa.Column("odometro_km", sa.Integer(), nullable=True),
        sa.Column("realizada_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("registrada_por", sa.Uuid(), nullable=True),
        sa.Column("client_action_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicio.id"]),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"]),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidad.id"]),
        sa.ForeignKeyConstraint(["registrada_por"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id"),
        sa.UniqueConstraint("client_action_id"),
    )

    op.create_table(
        "reporte_cierre",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("servicio_id", sa.Uuid(), nullable=False),
        sa.Column("operador_id", sa.Uuid(), nullable=False),
        sa.Column("nivel_combustible", sa.Numeric(), nullable=False),
        sa.Column("lectura_medidor", sa.JSON(), nullable=False),
        sa.Column("odometro_km", sa.Integer(), nullable=True),
        sa.Column("cargo_combustible", sa.Boolean(), nullable=False),
        sa.Column("observaciones", sa.String(), nullable=True),
        sa.Column("cerrado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("client_action_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicio.id"]),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id"),
        sa.UniqueConstraint("client_action_id"),
    )

    op.create_table(
        "carga_combustible",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("servicio_id", sa.Uuid(), nullable=True),
        sa.Column("unidad_id", sa.Uuid(), nullable=False),
        sa.Column("operador_id", sa.Uuid(), nullable=True),
        sa.Column("litros", sa.Numeric(), nullable=False),
        sa.Column("precio_litro", sa.Numeric(), nullable=False),
        sa.Column("importe", sa.Numeric(), nullable=False),
        sa.Column("tipo_combustible", sa.String(), nullable=True),
        sa.Column("ticket_key", sa.String(), nullable=True),
        sa.Column("cargada_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("registrada_por", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicio.id"]),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidad.id"]),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"]),
        sa.ForeignKeyConstraint(["registrada_por"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_carga_combustible_unidad_fecha", "carga_combustible", ["unidad_id", "cargada_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_carga_combustible_unidad_fecha", table_name="carga_combustible")
    op.drop_table("carga_combustible")
    op.drop_table("reporte_cierre")
    op.drop_table("inspeccion_salida")
