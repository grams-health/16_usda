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

    @patch("src.rest.search.search_usda_foods")
    def test_search_returns_json_on_non_rate_limit_exception(self, mock_search, client):
        from src.app.app import app as flask_app

        mock_search.side_effect = KeyError("nutrientName")
        flask_app.config["PROPAGATE_EXCEPTIONS"] = False
        try:
            resp = client.get("/usda/search?q=chicken")
        finally:
            flask_app.config.pop("PROPAGATE_EXCEPTIONS", None)
        assert resp.is_json, (
            f"Expected JSON response, got Content-Type={resp.content_type!r}, "
            f"body={resp.data[:200]!r}"
        )
        assert resp.status_code != 200
        assert 400 <= resp.status_code < 600
