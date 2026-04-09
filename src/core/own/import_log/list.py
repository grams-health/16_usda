from .db import get_session, ImportsRow


def is_imported(fdc_id: int) -> bool:
    session = get_session()
    try:
        row = session.query(ImportsRow).filter_by(fdc_id=fdc_id).first()
        return row is not None
    finally:
        session.close()


def list_imported_fdc_ids() -> set:
    session = get_session()
    try:
        rows = session.query(ImportsRow.fdc_id).all()
        return {row.fdc_id for row in rows}
    finally:
        session.close()
