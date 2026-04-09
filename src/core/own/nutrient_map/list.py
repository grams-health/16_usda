from .db import get_session, NutrientMapRow
from ...typing.nutrient_map import NutrientMapping


def list_nutrient_mappings() -> list:
    session = get_session()
    try:
        rows = session.query(NutrientMapRow).all()
        return [
            NutrientMapping(
                usda_number=row.usda_number,
                usda_name=row.usda_name,
                nutrient_name=row.nutrient_name,
            )
            for row in rows
        ]
    finally:
        session.close()


def get_mapping(usda_number: int):
    session = get_session()
    try:
        row = session.query(NutrientMapRow).filter_by(usda_number=usda_number).first()
        if row is None:
            return None
        return NutrientMapping(
            usda_number=row.usda_number,
            usda_name=row.usda_name,
            nutrient_name=row.nutrient_name,
        )
    finally:
        session.close()
