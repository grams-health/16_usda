import logging
import os

import pytest
from unittest.mock import patch, MagicMock


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
    """Pin the tightened failure contract for GET /usda/search.

    The diagnosis names the defect site as the body of handle_search in
    src/rest/search.py: its `except UsdaRateLimitError:` arm (search.py:14)
    is the only non-success exception arm, so any other exception raised in
    the view's call chain bubbles unhandled and Flask renders an opaque
    HTTP 500. We exercise that path by injecting a non-rate-limit failure
    at the HTTP boundary (`requests.get` in src/core/usda/client) so the
    full real call chain (handle_search -> service.search.search_usda_foods
    -> core.own.search.search_usda_foods -> core.usda.client.search_foods)
    executes naturally, then assert the contract: status != 500, JSON
    response, and an ERROR-level log carrying a traceback.

    Expected failure reason: this test will fail with AssertionError on
    `assert resp.status_code != 500` because handle_search at
    src/rest/search.py:14 only catches UsdaRateLimitError; the
    UsdaApiError raised by the boundary's 500 response escapes that
    narrow except clause and Flask's default error handler returns 500.
    """

    def test_does_not_500_on_non_rate_limit_upstream_failure(self, client, caplog, monkeypatch):
        monkeypatch.setenv("USDA_API_KEY", "test-key")
        client.application.config["PROPAGATE_EXCEPTIONS"] = False

        fake_response = MagicMock()
        fake_response.status_code = 500
        fake_response.json.return_value = {"foods": []}

        with patch("src.core.usda.client.requests.get", return_value=fake_response):
            with caplog.at_level(logging.ERROR):
                resp = client.get("/usda/search?q=chicken")

        assert resp.status_code != 500, (
            f"expected non-500 for upstream UsdaApiError, got {resp.status_code}"
        )
        assert resp.content_type.startswith("application/json"), (
            f"expected JSON content-type, got {resp.content_type}"
        )
        assert any(
            rec.levelno >= logging.ERROR and rec.exc_info for rec in caplog.records
        ), "expected an ERROR-level log record with traceback (exc_info) for the upstream exception"
