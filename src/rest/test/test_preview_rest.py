import pytest
from unittest.mock import patch
from ...core.usda.client import UsdaFoodNotFoundError


class TestPreviewRest:
    @patch("src.rest.preview.preview_usda_food")
    def test_preview_returns_food(self, mock_preview, client):
        mock_preview.return_value = {
            "fdc_id": 171077,
            "food_name": "Chicken breast",
            "food_category": "Poultry",
            "nutrients": [],
            "coverage": {"available": 0, "total": 32, "missing": []},
        }
        resp = client.get("/usda/preview/171077")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["fdc_id"] == 171077

    @patch("src.rest.preview.preview_usda_food")
    def test_preview_not_found(self, mock_preview, client):
        mock_preview.side_effect = UsdaFoodNotFoundError("not found")
        resp = client.get("/usda/preview/999999")
        assert resp.status_code == 404
