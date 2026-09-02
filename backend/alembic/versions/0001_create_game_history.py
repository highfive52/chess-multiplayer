"""create game history tables

Revision ID: 0001_create_game_history
Revises:
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_create_game_history"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ensure uuid extension available
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    op.create_table(
        "games",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("room_code", sa.String(length=32), nullable=True),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False, server_default="live"
        ),
        sa.Column("initial_fen", sa.Text(), nullable=False),
        sa.Column("final_fen", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="active"
        ),
        sa.Column("result", sa.String(length=16), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "game_moves",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("game_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False),
        sa.Column("san", sa.String(length=64), nullable=False),
        sa.Column("fen_after", sa.Text(), nullable=False),
        sa.Column("from_square", sa.String(length=8), nullable=True),
        sa.Column("to_square", sa.String(length=8), nullable=True),
        sa.Column("promotion", sa.String(length=8), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_foreign_key(
        "fk_game_moves_game",
        "game_moves",
        "games",
        ["game_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_game_moves_game_ply", "game_moves", ["game_id", "ply"]
    )
    op.create_index(
        "ix_game_moves_game_ply_desc",
        "game_moves",
        ["game_id", "ply"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_game_moves_game_ply_desc", table_name="game_moves")
    op.drop_constraint("uq_game_moves_game_ply", "game_moves", type_="unique")
    op.drop_constraint("fk_game_moves_game", "game_moves", type_="foreignkey")
    op.drop_table("game_moves")
    op.drop_table("games")
