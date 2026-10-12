"""lugares con RFC genérico de extranjeros (XEXX010101000) → genérico nacional

Todo el transporte es nacional (TranspInternac = "No"): el SAT rechaza XEXX… en
RFCRemitenteDestinatario. Venían así del Excel (CMI GROUP HOLDINGS, San Luis Potosí).

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE lugar SET rfc_remitente_destinatario = 'XAXX010101000' "
            "WHERE UPPER(TRIM(rfc_remitente_destinatario)) = 'XEXX010101000'"
        )
    )


def downgrade() -> None:
    pass  # no se puede saber cuáles eran; el valor anterior era inválido de todos modos
