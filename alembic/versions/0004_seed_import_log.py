"""Baseline current USDA import_log (as of 2026-04-19).

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-19

Captures the 8 USDA foods that have been imported into the admin food library
so far. `fdc_id` is the USDA FoodData Central id; `food_id` is the admin
foods table id (application-layer reference, no DB-level constraint).

Uses ON CONFLICT DO NOTHING so this migration is a no-op on DBs that already
have the rows (including today's running usda DB) and only seeds on fresh
databases.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


IMPORT_LOG = [
    # (fdc_id, food_id, food_name)
    (169291, 2, "Squash, summer, zucchini, includes skin, raw"),
    (170108, 4, "Peppers, sweet, red, raw"),
    (170393, 3, "Carrots, raw"),
    (170894, 8, "Yogurt, Greek, plain, nonfat (Includes foods for USDA's Food Distribution Program)"),
    (171077, 1, "Chicken, broiler or fryers, breast, skinless, boneless, meat only, raw"),
    (171287, 5, "Egg, whole, raw, fresh"),
    (172688, 7, "Bread, whole-wheat, commercially prepared"),
    (173430, 6, "Butter, without salt"),
]


def _q(s):
    return str(s).replace("'", "''")


def upgrade() -> None:
    for fdc_id, food_id, food_name in IMPORT_LOG:
        op.execute(
            f"INSERT INTO import_log (fdc_id, food_id, food_name) "
            f"VALUES ({fdc_id}, {food_id}, '{_q(food_name)}') "
            f"ON CONFLICT (fdc_id) DO NOTHING"
        )


def downgrade() -> None:
    fdc_ids = ", ".join(str(row[0]) for row in IMPORT_LOG)
    op.execute(f"DELETE FROM import_log WHERE fdc_id IN ({fdc_ids})")
