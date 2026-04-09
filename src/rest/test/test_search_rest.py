import pytest
from unittest.mock import patch


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
