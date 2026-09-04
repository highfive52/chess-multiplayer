"""add import provenance fields to games

Revision ID: 0002_add_import_fields
Revises: 0001_create_game_history
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_import_fields"
down_revision = "0001_create_game_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("source_filename", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "games",
        sa.Column("imported_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("games", "imported_at")
    op.drop_column("games", "source_filename")
