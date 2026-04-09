from .db import get_session, NutrientMapRow
from ...typing.status import Status


def remove_mapping(usda_number: int) -> Status:
    session = get_session()
    try:
        row = session.query(NutrientMapRow).filter_by(usda_number=usda_number).first()
        if row is None:
            return Status("error", f"Mapping for USDA #{usda_number} not found")
        session.delete(row)
        session.commit()
        return Status("success", f"Mapping removed for USDA #{usda_number}")
    finally:
        session.close()
