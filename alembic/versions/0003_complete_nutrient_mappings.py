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
    nutrient_map = sa.table(
        "nutrient_map",
        sa.column("usda_number", sa.Integer),
        sa.column("usda_name", sa.String),
        sa.column("nutrient_name", sa.String),
    )
    op.bulk_insert(nutrient_map, [
        {"usda_number": num, "usda_name": name, "nutrient_name": mapped}
        for num, name, mapped in ADDITIONS
    ])
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
