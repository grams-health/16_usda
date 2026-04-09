import pytest
from .. import db as nutrient_map_db


@pytest.fixture(autouse=True)
def setup_nutrient_map_db():
    nutrient_map_db.init_db("sqlite:///:memory:")
    yield
