"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrient_map",
        sa.Column("usda_number", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("usda_name", sa.String, nullable=False),
        sa.Column("nutrient_name", sa.String, nullable=False),
    )
    op.create_table(
        "import_log",
        sa.Column("fdc_id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("food_id", sa.Integer, nullable=False),
        sa.Column("food_name", sa.String, nullable=False),
        sa.Column("imported_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("import_log")
    op.drop_table("nutrient_map")
