import pytest
from unittest.mock import patch
from ...core.typing.status import Status
from ...core.usda.client import UsdaFoodNotFoundError


class TestImportRest:
    @patch("src.rest.import_food.import_usda_food")
    def test_import_success(self, mock_import, client):
        mock_import.return_value = Status("success", "Food imported with 2 nutrients", data={"food_id": 47})
        resp = client.post("/usda/import/171077")
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["food_id"] == 47

    @patch("src.rest.import_food.import_usda_food")
    def test_import_already_imported(self, mock_import, client):
        mock_import.return_value = Status("error", "Food 171077 already imported")
        resp = client.post("/usda/import/171077")
        assert resp.status_code == 409
