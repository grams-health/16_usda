import pytest
from src.core.database import init_db, reset, Base, get_engine
from src.app.app import app


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db("sqlite:///:memory:")
    Base.metadata.create_all(get_engine())
    yield
    reset()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
