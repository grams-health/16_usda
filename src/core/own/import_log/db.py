from sqlalchemy import Column, Integer, String, DateTime, func

from ...database import Base, get_session  # noqa: F401


class ImportsRow(Base):
    __tablename__ = "import_log"
    fdc_id = Column(Integer, primary_key=True, autoincrement=False)
    food_id = Column(Integer, nullable=False)
    food_name = Column(String, nullable=False)
    imported_at = Column(DateTime, default=func.now())
