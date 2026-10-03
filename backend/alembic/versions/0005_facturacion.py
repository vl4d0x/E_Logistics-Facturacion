"""fase 4 — facturacion (configuracion, factura)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_estado_factura = postgresql.ENUM(
    "timbrada", "cancelacion_pendiente", "cancelada", "error", name="estadofactura", create_type=False
)
_estado_cobro = postgresql.ENUM("pendiente", "parcial", "pagada", name="estadocobro", create_type=False)

_envio_destinatarios_type = sa.JSON().with_variant(postgresql.ARRAY(sa.String()), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    _estado_factura.create(bind, checkfirst=True)
    _estado_cobro.create(bind, checkfirst=True)

    op.create_table(
        "configuracion",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("clave", sa.String(), nullable=False),
        sa.Column("valor", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("clave"),
    )

    op.create_table(
        "factura",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("servicio_id", sa.Uuid(), nullable=False),
        sa.Column("estado", _estado_factura, nullable=False),
        sa.Column("uuid_fiscal", sa.String(), nullable=True),
        sa.Column("serie", sa.String(), nullable=True),
        sa.Column("folio", sa.String(), nullable=True),
        sa.Column("fecha_emision", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("metodo_pago", sa.String(), nullable=False),
        sa.Column("forma_pago", sa.String(), nullable=False),
        sa.Column("uso_cfdi", sa.String(), nullable=False),
        sa.Column("subtotal", sa.Numeric(), nullable=False),
        sa.Column("iva_trasladado", sa.Numeric(), nullable=False),
        sa.Column("iva_retenido", sa.Numeric(), nullable=False),
        sa.Column("total", sa.Numeric(), nullable=False),
        sa.Column("saldo_insoluto", sa.Numeric(), nullable=False),
        sa.Column("estado_cobro", _estado_cobro, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("facturama_id", sa.String(), nullable=True),
        sa.Column("xml_key", sa.String(), nullable=True),
        sa.Column("pdf_key", sa.String(), nullable=True),
        sa.Column("error_detalle", sa.String(), nullable=True),
        sa.Column("motivo_cancelacion", sa.String(), nullable=True),
        sa.Column("uuid_sustitucion", sa.String(), nullable=True),
        sa.Column("cancelacion_solicitada_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("cancelada_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("acuse_cancelacion_key", sa.String(), nullable=True),
        sa.Column("estatus_consultado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("enviado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("envio_destinatarios", _envio_destinatarios_type, nullable=True),
        sa.Column("envio_error", sa.String(), nullable=True),
        sa.Column("timbrado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["servicio_id"], ["servicio.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid_fiscal"),
    )
    op.create_index("ix_factura_servicio_id", "factura", ["servicio_id"])
    op.create_index("ix_factura_estado_fecha_emision", "factura", ["estado", "fecha_emision"])
    op.create_index("ix_factura_estado_cobro", "factura", ["estado_cobro"])
    op.create_index(
        "uq_factura_servicio_vigente",
        "factura",
        ["servicio_id"],
        unique=True,
        postgresql_where=sa.text("estado IN ('timbrada', 'cancelacion_pendiente')"),
        sqlite_where=sa.text("estado IN ('timbrada', 'cancelacion_pendiente')"),
    )


def downgrade() -> None:
    op.drop_index("uq_factura_servicio_vigente", table_name="factura")
    op.drop_index("ix_factura_estado_cobro", table_name="factura")
    op.drop_index("ix_factura_estado_fecha_emision", table_name="factura")
    op.drop_index("ix_factura_servicio_id", table_name="factura")
    op.drop_table("factura")
    op.drop_table("configuracion")

    bind = op.get_bind()
    _estado_cobro.drop(bind, checkfirst=True)
    _estado_factura.drop(bind, checkfirst=True)
