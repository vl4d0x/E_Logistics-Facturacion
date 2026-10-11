"""km por lugar (lugar.distancia_km/km_confirmado) y CP por viaje (viaje.origen_cp/destino_cp)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lugar", sa.Column("distancia_km", sa.Float(), nullable=True))
    op.add_column(
        "lugar",
        sa.Column("km_confirmado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("viaje", sa.Column("origen_cp", sa.String(), nullable=True))
    op.add_column("viaje", sa.Column("destino_cp", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("viaje", "destino_cp")
    op.drop_column("viaje", "origen_cp")
    op.drop_column("lugar", "km_confirmado")
    op.drop_column("lugar", "distancia_km")
