import pytest
from .. import db as import_log_db


@pytest.fixture(autouse=True)
def setup_import_log_db():
    import_log_db.init_db("sqlite:///:memory:")
    yield
