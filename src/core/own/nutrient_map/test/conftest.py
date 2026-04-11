import pytest
from src.core.database import init_db, reset, Base, get_engine


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db("sqlite:///:memory:")
    Base.metadata.create_all(get_engine())
    yield
    reset()
