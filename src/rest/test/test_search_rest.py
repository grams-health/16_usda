import pytest
from unittest.mock import patch

from src.core.usda.client import UsdaApiError


class TestSearchRest:
    def test_search_missing_query(self, client):
        resp = client.get("/usda/search")
        assert resp.status_code == 400

    def test_search_empty_query(self, client):
        resp = client.get("/usda/search?q=")
        assert resp.status_code == 400

    @patch("src.rest.search.search_usda_foods")
    def test_search_returns_results(self, mock_search, client):
        mock_search.return_value = [
            {"fdc_id": 171077, "description": "Chicken breast", "food_category": "Poultry", "imported": False},
        ]
        resp = client.get("/usda/search?q=chicken")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["results"]) == 1
        assert data["results"][0]["fdc_id"] == 171077

    @patch("src.rest.search.search_usda_foods")
    def test_search_upstream_non_200_returns_502_json(self, mock_search, client):
        mock_search.side_effect = UsdaApiError("USDA API error: 404")
        resp = client.get("/usda/search?q=chicken")
        assert resp.status_code == 502
        assert resp.is_json
        data = resp.get_json()
        assert data["status"] == "error"
        assert isinstance(data.get("message"), str) and data["message"]
