"""Complete USDA nutrient mappings.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-19

Adds USDA 507 (Cystine) and 509 (Tyrosine) — paired amino acids that both map
into the admin's combined "Methionine + Cysteine" and "Phenylalanine + Tyrosine"
nutrients. Also corrects the usda_name for 269 (Total Sugars) to match the
modern FoodData Central spelling.

Previously these extras only lived in platform/seed/data.ts and were added by
`make seed`. Moved into Alembic so a fresh USDA DB has the full mapping set.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ADDITIONS = [
    (507, "Cystine", "Methionine + Cysteine"),
    (509, "Tyrosine", "Phenylalanine + Tyrosine"),
]


def upgrade() -> None:
    # Idempotent upserts — some environments added 507/509 via the old
    # platform seed path before this migration existed.
    for num, name, mapped in ADDITIONS:
        op.execute(
            f"INSERT INTO nutrient_map (usda_number, usda_name, nutrient_name) "
            f"VALUES ({num}, '{name}', '{mapped}') "
            f"ON CONFLICT (usda_number) DO NOTHING"
        )
    # Correct the usda_name for 269 to match the modern USDA spelling.
    op.execute(
        "UPDATE nutrient_map SET usda_name = 'Sugars, total including NLEA' "
        "WHERE usda_number = 269"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE nutrient_map SET usda_name = 'Sugars, Total' "
        "WHERE usda_number = 269"
    )
    op.execute("DELETE FROM nutrient_map WHERE usda_number IN (507, 509)")
