import logging

import pytest
from sqlalchemy.exc import SQLAlchemyError
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


class TestSearchFailureContract:
    """Verify GET /usda/search obeys the tightened failure contract:
    non-rate-limit exceptions from the view's call chain must NOT surface
    as HTTP 500; they must return a deterministic non-500 JSON response
    with an ERROR log carrying the full traceback.
    """

    @patch("src.rest.search.search_usda_foods")
    def test_does_not_500_on_usda_api_error(self, mock_search, client, caplog):
        from src.core.usda.client import UsdaApiError

        mock_search.side_effect = UsdaApiError("USDA API error: 500")
        client.application.config["PROPAGATE_EXCEPTIONS"] = False
        with caplog.at_level(logging.ERROR):
            resp = client.get("/usda/search?q=chicken")
        assert resp.status_code != 500, (
            f"expected non-500 for UsdaApiError, got {resp.status_code}"
        )
        assert resp.content_type.startswith("application/json")
        assert any(rec.levelno >= logging.ERROR and rec.exc_info for rec in caplog.records), (
            "expected an ERROR-level log record with traceback (exc_info) for the injected exception"
        )

    @patch("src.rest.search.search_usda_foods")
    def test_does_not_500_on_payload_key_error(self, mock_search, client, caplog):
        mock_search.side_effect = KeyError("fdcId")
        client.application.config["PROPAGATE_EXCEPTIONS"] = False
        with caplog.at_level(logging.ERROR):
            resp = client.get("/usda/search?q=chicken")
        assert resp.status_code != 500, (
            f"expected non-500 for KeyError, got {resp.status_code}"
        )
        assert resp.content_type.startswith("application/json")
        assert any(rec.levelno >= logging.ERROR and rec.exc_info for rec in caplog.records), (
            "expected an ERROR-level log record with traceback for the injected KeyError"
        )

    @patch("src.rest.search.search_usda_foods")
    def test_does_not_500_on_sqlalchemy_error(self, mock_search, client, caplog):
        mock_search.side_effect = SQLAlchemyError("simulated import_log lookup failure")
        client.application.config["PROPAGATE_EXCEPTIONS"] = False
        with caplog.at_level(logging.ERROR):
            resp = client.get("/usda/search?q=chicken")
        assert resp.status_code != 500, (
            f"expected non-500 for SQLAlchemyError, got {resp.status_code}"
        )
        assert resp.content_type.startswith("application/json")
        assert any(rec.levelno >= logging.ERROR and rec.exc_info for rec in caplog.records), (
            "expected an ERROR-level log record with traceback for the injected SQLAlchemyError"
        )

    @patch("src.rest.search.search_usda_foods")
    def test_does_not_500_on_unexpected_exception(self, mock_search, client, caplog):
        mock_search.side_effect = RuntimeError("unanticipated downstream failure")
        client.application.config["PROPAGATE_EXCEPTIONS"] = False
        with caplog.at_level(logging.ERROR):
            resp = client.get("/usda/search?q=chicken")
        assert resp.status_code != 500, (
            f"expected non-500 for unexpected RuntimeError, got {resp.status_code}"
        )
        assert resp.content_type.startswith("application/json")
        assert any(rec.levelno >= logging.ERROR and rec.exc_info for rec in caplog.records), (
            "expected an ERROR-level log record with traceback for the unexpected exception"
        )
