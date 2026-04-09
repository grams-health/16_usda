from ..create import record_import
from ..list import is_imported, list_imported_fdc_ids


class TestImportLog:
    def test_record_import(self):
        status = record_import(171077, 47, "Chicken breast")
        assert status
        assert status.status == "success"

    def test_is_imported_true(self):
        record_import(171077, 47, "Chicken breast")
        assert is_imported(171077) is True

    def test_is_imported_false(self):
        assert is_imported(999999) is False

    def test_list_imported_fdc_ids(self):
        record_import(171077, 47, "Chicken breast")
        record_import(171078, 48, "Chicken thigh")
        ids = list_imported_fdc_ids()
        assert ids == {171077, 171078}
