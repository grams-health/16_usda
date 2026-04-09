from sqlalchemy.exc import IntegrityError
from .db import get_session, NutrientMapRow
from ...typing.status import Status


def create_mapping(usda_number: int, usda_name: str, nutrient_name: str) -> Status:
    session = get_session()
    try:
        row = NutrientMapRow(
            usda_number=usda_number,
            usda_name=usda_name,
            nutrient_name=nutrient_name,
        )
        session.add(row)
        session.commit()
        return Status("success", f"Mapping created for USDA #{usda_number}")
    except IntegrityError:
        session.rollback()
        return Status("error", f"Mapping for USDA #{usda_number} already exists")
    finally:
        session.close()
