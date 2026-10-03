"""fase 2 — servicios y viajes (servicio, viaje, viaje_mercancia, acuse)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_estado_servicio = postgresql.ENUM(
    "programado", "en_curso", "terminado", "cancelado", name="estadoservicio", create_type=False
)
_estado_facturacion = postgresql.ENUM(
    "pendiente", "facturado", name="estadofacturacion", create_type=False
)
_tipo_viaje = postgresql.ENUM(
    "recoleccion", "entrega", "recoleccion_entrega", name="tipoviaje", create_type=False
)
_estado_viaje = postgresql.ENUM("pendiente", "terminado", name="estadoviaje", create_type=False)
_tipo_acuse = postgresql.ENUM("escaneo", "referencia", name="tipoacuse", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    _estado_servicio.create(bind, checkfirst=True)
    _estado_facturacion.create(bind, checkfirst=True)
    _tipo_viaje.create(bind, checkfirst=True)
    _estado_viaje.create(bind, checkfirst=True)
    _tipo_acuse.create(bind, checkfirst=True)

    op.create_table(
        "servicio",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("unidad_id", sa.Uuid(), nullable=False),
        sa.Column("operador_id", sa.Uuid(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("estado", _estado_servicio, nullable=False),
        sa.Column("estado_facturacion", _estado_facturacion, nullable=False),
        sa.Column("timbrado_anticipado", sa.Boolean(), nullable=False),
        sa.Column("subtotal", sa.Numeric(), nullable=True),
        sa.Column("descripcion_concepto", sa.String(), nullable=True),
        sa.Column("metodo_pago", sa.String(), nullable=True),
        sa.Column("uso_cfdi", sa.String(), nullable=True),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column("iniciado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("terminado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("terminado_por_admin", sa.Boolean(), nullable=False),
        sa.Column("cancelado_motivo", sa.String(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidad.id"]),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_servicio_numero"), "servicio", ["numero"], unique=True)
    op.create_index(op.f("ix_servicio_cliente_id"), "servicio", ["cliente_id"])
    op.create_index(op.f("ix_servicio_unidad_id"), "servicio", ["unidad_id"])
    op.create_index(op.f("ix_servicio_operador_id"), "servicio", ["operador_id"])

    op.create_table(
        "viaje",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("servicio_id", sa.Uuid(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("tipo", _tipo_viaje, nullable=False),
        sa.Column("estado", _estado_viaje, nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("hora_salida_programada", sa.Time(), nullable=True),
        sa.Column("hora_llegada_programada", sa.Time(), nullable=True),
        sa.Column("origen_lugar_id", sa.Uuid(), nullable=True),
        sa.Column("destino_lugar_id", sa.Uuid(), nullable=True),
        sa.Column("distancia_km", sa.Float(), nullable=True),
        sa.Column("km_reportado", sa.Float(), nullable=True),
        sa.Column("hora_llegada", sa.Time(), nullable=True),
        sa.Column("terminado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("terminado_por", sa.Uuid(), nullable=True),
        sa.Column("notas_admin", sa.String(), nullable=True),
        sa.Column("notas_operador", sa.String(), nullable=True),
        sa.Column("client_action_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicio.id"]),
        sa.ForeignKeyConstraint(["origen_lugar_id"], ["lugar.id"]),
        sa.ForeignKeyConstraint(["destino_lugar_id"], ["lugar.id"]),
        sa.ForeignKeyConstraint(["terminado_por"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("servicio_id", "orden", name="uq_viaje_servicio_orden"),
        sa.UniqueConstraint("client_action_id"),
    )
    op.create_index(op.f("ix_viaje_servicio_id"), "viaje", ["servicio_id"])

    op.create_table(
        "viaje_mercancia",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("viaje_id", sa.Uuid(), nullable=False),
        sa.Column("mercancia_frecuente_id", sa.Uuid(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("bienes_transp", sa.String(), nullable=False),
        sa.Column("clave_unidad", sa.String(), nullable=False),
        sa.Column("unidad_desc", sa.String(), nullable=True),
        sa.Column("cantidad", sa.Numeric(), nullable=False),
        sa.Column("peso_kg", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["viaje_id"], ["viaje.id"]),
        sa.ForeignKeyConstraint(["mercancia_frecuente_id"], ["mercancia_frecuente.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_viaje_mercancia_viaje_id"), "viaje_mercancia", ["viaje_id"])

    op.create_table(
        "acuse",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("viaje_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", _tipo_acuse, nullable=False),
        sa.Column("archivo_key", sa.String(), nullable=True),
        sa.Column("mime", sa.String(), nullable=True),
        sa.Column("pagina", sa.Integer(), nullable=False),
        sa.Column("referencia", sa.String(), nullable=True),
        sa.Column("subido_por", sa.Uuid(), nullable=True),
        sa.Column("subido_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("client_action_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["viaje_id"], ["viaje.id"]),
        sa.ForeignKeyConstraint(["subido_por"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_action_id"),
    )
    op.create_index(op.f("ix_acuse_viaje_id"), "acuse", ["viaje_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_acuse_viaje_id"), table_name="acuse")
    op.drop_table("acuse")

    op.drop_index(op.f("ix_viaje_mercancia_viaje_id"), table_name="viaje_mercancia")
    op.drop_table("viaje_mercancia")

    op.drop_index(op.f("ix_viaje_servicio_id"), table_name="viaje")
    op.drop_table("viaje")

    op.drop_index(op.f("ix_servicio_operador_id"), table_name="servicio")
    op.drop_index(op.f("ix_servicio_unidad_id"), table_name="servicio")
    op.drop_index(op.f("ix_servicio_cliente_id"), table_name="servicio")
    op.drop_index(op.f("ix_servicio_numero"), table_name="servicio")
    op.drop_table("servicio")

    bind = op.get_bind()
    _tipo_acuse.drop(bind, checkfirst=True)
    _estado_viaje.drop(bind, checkfirst=True)
    _tipo_viaje.drop(bind, checkfirst=True)
    _estado_facturacion.drop(bind, checkfirst=True)
    _estado_servicio.drop(bind, checkfirst=True)
