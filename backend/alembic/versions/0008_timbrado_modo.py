"""servicio.timbrado_modo — timbrar con $0.10 y cancelar (anticipado sin precio)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "servicio",
        sa.Column("timbrado_modo", sa.String(), nullable=False, server_default="precio"),
    )


def downgrade() -> None:
    op.drop_column("servicio", "timbrado_modo")
