"""servicio.sin_carta_porte: factura de ingreso sin el complemento Carta Porte

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-11

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "servicio", sa.Column("sin_carta_porte", sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column("servicio", "sin_carta_porte")
