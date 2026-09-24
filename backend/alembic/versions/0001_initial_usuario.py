"""initial — tabla usuario

Revision ID: 0001
Revises:
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_rol_usuario = sa.Enum("admin", "operador", name="rolusuario")


def upgrade() -> None:
    _rol_usuario.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("rol", _rol_usuario, nullable=False),
        sa.Column("operador_id", sa.Uuid(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuario_email"), "usuario", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_usuario_email"), table_name="usuario")
    op.drop_table("usuario")
    _rol_usuario.drop(op.get_bind(), checkfirst=True)
