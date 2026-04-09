from .db import get_session, NutrientMapRow
from ...typing.status import Status


def modify_mapping(usda_number: int, nutrient_name: str) -> Status:
    session = get_session()
    try:
        row = session.query(NutrientMapRow).filter_by(usda_number=usda_number).first()
        if row is None:
            return Status("error", f"Mapping for USDA #{usda_number} not found")
        row.nutrient_name = nutrient_name
        session.commit()
        return Status("success", f"Mapping updated for USDA #{usda_number}")
    finally:
        session.close()
