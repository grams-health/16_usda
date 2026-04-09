from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_Session = None


class NutrientMapRow(Base):
    __tablename__ = "nutrient_map"
    usda_number = Column(Integer, primary_key=True, autoincrement=False)
    usda_name = Column(String, nullable=False)
    nutrient_name = Column(String, nullable=False)


def init_db(url: str):
    global _engine, _Session
    _engine = create_engine(url)
    _Session = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)


def get_session():
    if _Session is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _Session()
