"""Seed USDA nutrient mappings from admin nutrient reference data.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Source: admin service 0002_seed_nutrient_reference_data.py
# Each entry: (usda_number, usda_name, nutrient_name)
MAPPINGS = [
    # Macronutrients
    (203, "Protein", "Protein"),
    (205, "Carbohydrate, by difference", "Carbohydrates"),
    (204, "Total lipid (fat)", "Fat"),
    (291, "Fiber, total dietary", "Fiber"),
    (208, "Energy", "Calories"),

    # Amino Acids
    (512, "Histidine", "Histidine"),
    (503, "Isoleucine", "Isoleucine"),
    (504, "Leucine", "Leucine"),
    (505, "Lysine", "Lysine"),
    (506, "Methionine", "Methionine + Cysteine"),
    (508, "Phenylalanine", "Phenylalanine + Tyrosine"),
    (502, "Threonine", "Threonine"),
    (501, "Tryptophan", "Tryptophan"),
    (510, "Valine", "Valine"),

    # Fat Sub-types
    (606, "Fatty acids, total saturated", "Saturated Fat"),
    (645, "Fatty acids, total monounsaturated", "Monounsaturated Fat"),
    (646, "Fatty acids, total polyunsaturated", "Polyunsaturated Fat"),
    (605, "Fatty acids, total trans", "Trans Fat"),
    (619, "18:3 n-3 c,c,c (ALA)", "Omega-3 (ALA)"),
    (618, "18:2 n-6 c,c (LA)", "Omega-6 (LA)"),
    (601, "Cholesterol", "Cholesterol"),

    # Carb Sub-types
    (209, "Starch", "Starch"),
    (269, "Sugars, Total", "Total Sugars"),

    # Minerals
    (303, "Iron, Fe", "Iron"),
    (301, "Calcium, Ca", "Calcium"),
    (304, "Magnesium, Mg", "Magnesium"),
    (309, "Zinc, Zn", "Zinc"),
    (306, "Potassium, K", "Potassium"),
    (307, "Sodium, Na", "Sodium"),

    # Vitamins
    (328, "Vitamin D (D2 + D3)", "Vitamin D"),
    (418, "Vitamin B-12", "Vitamin B12"),
    (417, "Folate, total", "Folate"),
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
        for num, name, mapped in MAPPINGS
    ])


def downgrade() -> None:
    op.execute("DELETE FROM nutrient_map")
