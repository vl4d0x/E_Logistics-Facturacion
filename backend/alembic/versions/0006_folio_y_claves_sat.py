"""folio de cliente en concepto + claves SAT cacheadas en lugar

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cliente",
        sa.Column("requiere_folio_concepto", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("cliente", "requiere_folio_concepto", server_default=None)

    op.add_column("lugar", sa.Column("municipio_clave", sa.String(), nullable=True))
    op.add_column("lugar", sa.Column("localidad_clave", sa.String(), nullable=True))

    op.add_column("servicio", sa.Column("folio_cliente", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("servicio", "folio_cliente")
    op.drop_column("lugar", "localidad_clave")
    op.drop_column("lugar", "municipio_clave")
    op.drop_column("cliente", "requiere_folio_concepto")
