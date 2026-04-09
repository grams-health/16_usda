from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_Session = None


class ImportsRow(Base):
    __tablename__ = "import_log"
    fdc_id = Column(Integer, primary_key=True, autoincrement=False)
    food_id = Column(Integer, nullable=False)
    food_name = Column(String, nullable=False)
    imported_at = Column(DateTime, default=func.now())


def init_db(url: str):
    global _engine, _Session
    _engine = create_engine(url)
    _Session = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)


def get_session():
    if _Session is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _Session()
