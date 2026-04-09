import pytest
from ...core.own.import_log import db as import_log_db
from ...core.own.nutrient_map import db as nutrient_map_db
from ...app.app import app


@pytest.fixture(autouse=True)
def setup_dbs():
    import_log_db.init_db("sqlite:///:memory:")
    nutrient_map_db.init_db("sqlite:///:memory:")
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
