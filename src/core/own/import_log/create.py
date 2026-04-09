from sqlalchemy.exc import IntegrityError
from .db import get_session, ImportsRow
from ...typing.status import Status


def record_import(fdc_id: int, food_id: int, food_name: str) -> Status:
    session = get_session()
    try:
        row = ImportsRow(fdc_id=fdc_id, food_id=food_id, food_name=food_name)
        session.add(row)
        session.commit()
        return Status("success", f"Import recorded for fdc_id {fdc_id}")
    except IntegrityError:
        session.rollback()
        return Status("error", f"fdc_id {fdc_id} already imported")
    finally:
        session.close()
