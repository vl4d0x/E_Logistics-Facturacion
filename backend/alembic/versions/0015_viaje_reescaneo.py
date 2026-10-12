"""viaje: etiqueta "Re-escaneo" del acuse (motivo, cuándo y quién la pidió)

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("viaje", sa.Column("reescaneo_motivo", sa.String(), nullable=True))
    op.add_column("viaje", sa.Column("reescaneo_solicitado_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True))
    op.add_column("viaje", sa.Column("reescaneo_solicitado_por", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_viaje_reescaneo_por", "viaje", "usuario", ["reescaneo_solicitado_por"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_viaje_reescaneo_por", "viaje", type_="foreignkey")
    for col in ("reescaneo_solicitado_por", "reescaneo_solicitado_at", "reescaneo_motivo"):
        op.drop_column("viaje", col)
