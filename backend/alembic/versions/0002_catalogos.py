"""fase 1 — catálogos (unidad, operador, cliente, mercancia_frecuente, lugar)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mismo patrón que 0001: create_type=False, el CREATE/DROP explícito (checkfirst=True)
# es la única fuente, así op.create_table() no intenta crearlos otra vez por su cuenta.
_tipo_medidor = postgresql.ENUM("aguja", "barras", name="tipomedidor", create_type=False)
_regimen_receptor = postgresql.ENUM("fisica", "moral", name="regimenreceptor", create_type=False)
_metodo_pago = postgresql.ENUM("PUE", "PPD", name="metodopago", create_type=False)
_modo_acuse = postgresql.ENUM(
    "escaneo", "referencia", "ninguno", name="modoacuse", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    _tipo_medidor.create(bind, checkfirst=True)
    _regimen_receptor.create(bind, checkfirst=True)
    _metodo_pago.create(bind, checkfirst=True)
    _modo_acuse.create(bind, checkfirst=True)

    op.create_table(
        "unidad",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("apodo", sa.String(), nullable=False),
        sa.Column("placa", sa.String(), nullable=False),
        sa.Column("anio_modelo", sa.Integer(), nullable=True),
        sa.Column("config_vehicular", sa.String(), nullable=False),
        sa.Column("peso_bruto_vehicular", sa.Float(), nullable=False),
        sa.Column("capacidad_carga_kg", sa.Float(), nullable=True),
        sa.Column("perm_sct", sa.String(), nullable=False),
        sa.Column("num_permiso_sct", sa.String(), nullable=False),
        sa.Column("aseguradora_resp_civil", sa.String(), nullable=True),
        sa.Column("poliza_resp_civil", sa.String(), nullable=True),
        sa.Column("tipo_medidor", _tipo_medidor, nullable=False),
        sa.Column("num_barras", sa.Integer(), nullable=True),
        sa.Column("capacidad_tanque_l", sa.Float(), nullable=True),
        sa.Column("tipo_combustible", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "tipo_medidor <> 'barras' OR (num_barras >= 2 AND num_barras <= 20)",
            name="ck_unidad_num_barras",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_unidad_apodo"), "unidad", ["apodo"], unique=True)
    op.create_index(op.f("ix_unidad_placa"), "unidad", ["placa"], unique=True)

    op.create_table(
        "operador",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("rfc", sa.String(), nullable=False),
        sa.Column("num_licencia", sa.String(), nullable=False),
        sa.Column("telefono", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cliente",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("razon_social", sa.String(), nullable=False),
        sa.Column("nombre_comercial", sa.String(), nullable=False),
        sa.Column("rfc", sa.String(), nullable=False),
        sa.Column("cp_fiscal", sa.String(), nullable=False),
        sa.Column("regimen_fiscal", sa.String(), nullable=False),
        sa.Column("regimen_receptor", _regimen_receptor, nullable=False),
        sa.Column("uso_cfdi", sa.String(), nullable=False),
        sa.Column("metodo_pago_default", _metodo_pago, nullable=False),
        sa.Column("modo_acuse", _modo_acuse, nullable=False),
        sa.Column("emails_facturacion", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("dias_credito", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "mercancia_frecuente",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("nombre_humano", sa.String(), nullable=False),
        sa.Column("bienes_transp", sa.String(), nullable=False),
        sa.Column("clave_unidad", sa.String(), nullable=False),
        sa.Column("unidad_desc", sa.String(), nullable=True),
        sa.Column("peso_kg_sugerido", sa.Float(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mercancia_frecuente_cliente_id"), "mercancia_frecuente", ["cliente_id"]
    )

    op.create_table(
        "lugar",
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("rfc_remitente_destinatario", sa.String(), nullable=False),
        sa.Column("nombre_remitente_destinatario", sa.String(), nullable=True),
        sa.Column("calle", sa.String(), nullable=True),
        sa.Column("num_exterior", sa.String(), nullable=True),
        sa.Column("colonia", sa.String(), nullable=True),
        sa.Column("localidad", sa.String(), nullable=True),
        sa.Column("municipio", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("pais", sa.String(), nullable=False),
        sa.Column("codigo_postal", sa.String(), nullable=False),
        sa.Column("referencia", sa.String(), nullable=True),
        sa.Column("es_origen_predeterminado", sa.Boolean(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lugar_cliente_id"), "lugar", ["cliente_id"])

    # `usuario.operador_id` existe desde Fase 0 sin FK/unique (02-data-model §3.1, H1.2).
    op.create_foreign_key(
        "fk_usuario_operador_id", "usuario", "operador", ["operador_id"], ["id"]
    )
    op.create_unique_constraint("uq_usuario_operador_id", "usuario", ["operador_id"])


def downgrade() -> None:
    op.drop_constraint("uq_usuario_operador_id", "usuario", type_="unique")
    op.drop_constraint("fk_usuario_operador_id", "usuario", type_="foreignkey")

    op.drop_index(op.f("ix_lugar_cliente_id"), table_name="lugar")
    op.drop_table("lugar")

    op.drop_index(op.f("ix_mercancia_frecuente_cliente_id"), table_name="mercancia_frecuente")
    op.drop_table("mercancia_frecuente")

    op.drop_table("cliente")
    op.drop_table("operador")

    op.drop_index(op.f("ix_unidad_placa"), table_name="unidad")
    op.drop_index(op.f("ix_unidad_apodo"), table_name="unidad")
    op.drop_table("unidad")

    bind = op.get_bind()
    _modo_acuse.drop(bind, checkfirst=True)
    _metodo_pago.drop(bind, checkfirst=True)
    _regimen_receptor.drop(bind, checkfirst=True)
    _tipo_medidor.drop(bind, checkfirst=True)
