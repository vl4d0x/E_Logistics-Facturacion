"""fase 5 — cobranza (pago, pago_aplicacion, rep)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_estado_pago = postgresql.ENUM("registrado", "aplicado", "rep_emitido", name="estadopago", create_type=False)
_estado_rep = postgresql.ENUM(
    "timbrado", "cancelacion_pendiente", "cancelado", "error", name="estadorep", create_type=False
)


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    _estado_pago.create(bind, checkfirst=True)
    _estado_rep.create(bind, checkfirst=True)

    op.create_table(
        "pago",
        *_ts(),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("fecha_pago", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("forma_pago", sa.String(), nullable=False),
        sa.Column("moneda", sa.String(), nullable=False),
        sa.Column("num_operacion", sa.String(), nullable=True),
        sa.Column("rfc_emisor_cta_ord", sa.String(), nullable=True),
        sa.Column("cta_ordenante", sa.String(), nullable=True),
        sa.Column("rfc_emisor_cta_ben", sa.String(), nullable=True),
        sa.Column("cta_beneficiario", sa.String(), nullable=True),
        sa.Column("comprobante_key", sa.String(), nullable=True),
        sa.Column("notas", sa.String(), nullable=True),
        sa.Column("estado", _estado_pago, nullable=False),
        sa.Column("aplicado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pago_cliente_id", "pago", ["cliente_id"])

    op.create_table(
        "pago_aplicacion",
        *_ts(),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pago_id", sa.Uuid(), nullable=False),
        sa.Column("factura_id", sa.Uuid(), nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("num_parcialidad", sa.Integer(), nullable=False),
        sa.Column("saldo_anterior", sa.Numeric(12, 2), nullable=False),
        sa.Column("saldo_insoluto", sa.Numeric(12, 2), nullable=False),
        sa.Column("base", sa.Numeric(12, 2), nullable=False),
        sa.Column("traslado", sa.Numeric(12, 2), nullable=False),
        sa.Column("retencion", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["pago_id"], ["pago.id"]),
        sa.ForeignKeyConstraint(["factura_id"], ["factura.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pago_id", "factura_id", name="uq_pago_aplicacion_pago_factura"),
    )
    op.create_index("ix_pago_aplicacion_pago_id", "pago_aplicacion", ["pago_id"])
    op.create_index("ix_pago_aplicacion_factura_id", "pago_aplicacion", ["factura_id"])

    op.create_table(
        "rep",
        *_ts(),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pago_id", sa.Uuid(), nullable=False),
        sa.Column("estado", _estado_rep, nullable=False),
        sa.Column("uuid_fiscal", sa.String(), nullable=True),
        sa.Column("serie", sa.String(), nullable=True),
        sa.Column("folio", sa.String(), nullable=True),
        sa.Column("fecha_emision", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("facturama_id", sa.String(), nullable=True),
        sa.Column("xml_key", sa.String(), nullable=True),
        sa.Column("pdf_key", sa.String(), nullable=True),
        sa.Column("error_detalle", sa.String(), nullable=True),
        sa.Column("motivo_cancelacion", sa.String(), nullable=True),
        sa.Column("uuid_sustitucion", sa.String(), nullable=True),
        sa.Column("cancelacion_solicitada_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("cancelado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("acuse_cancelacion_key", sa.String(), nullable=True),
        sa.Column("estatus_consultado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("enviado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.Column("timbrado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["pago_id"], ["pago.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid_fiscal"),
    )
    op.create_index("ix_rep_pago_id", "rep", ["pago_id"])
    op.create_index(
        "uq_rep_pago_vigente",
        "rep",
        ["pago_id"],
        unique=True,
        postgresql_where=sa.text("estado IN ('timbrado', 'cancelacion_pendiente')"),
        sqlite_where=sa.text("estado IN ('timbrado', 'cancelacion_pendiente')"),
    )


def downgrade() -> None:
    op.drop_index("uq_rep_pago_vigente", table_name="rep")
    op.drop_index("ix_rep_pago_id", table_name="rep")
    op.drop_table("rep")
    op.drop_index("ix_pago_aplicacion_factura_id", table_name="pago_aplicacion")
    op.drop_index("ix_pago_aplicacion_pago_id", table_name="pago_aplicacion")
    op.drop_table("pago_aplicacion")
    op.drop_index("ix_pago_cliente_id", table_name="pago")
    op.drop_table("pago")
    bind = op.get_bind()
    _estado_rep.drop(bind, checkfirst=True)
    _estado_pago.drop(bind, checkfirst=True)
