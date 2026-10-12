"""mercancía: declarar "MaterialPeligroso: No" (claves de c_ClaveProdServCP que lo exigen)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for tabla in ("mercancia_frecuente", "viaje_mercancia"):
        op.add_column(
            tabla,
            sa.Column("declarar_material_peligroso", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    for tabla in ("viaje_mercancia", "mercancia_frecuente"):
        op.drop_column(tabla, "declarar_material_peligroso")
