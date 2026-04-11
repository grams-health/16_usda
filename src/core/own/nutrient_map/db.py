from sqlalchemy import Column, Integer, String

from ...database import Base, get_session  # noqa: F401


class NutrientMapRow(Base):
    __tablename__ = "nutrient_map"
    usda_number = Column(Integer, primary_key=True, autoincrement=False)
    usda_name = Column(String, nullable=False)
    nutrient_name = Column(String, nullable=False)
