import json
import os
import pytest
from unittest.mock import patch, MagicMock
from ..usda.client import (
    UsdaApiError,
    UsdaConfigError,
    UsdaFoodNotFoundError,
    UsdaRateLimitError,
    UsdaTransientError,
    get_food,
    ip_health_snapshot,
    reset_ip_health,
    search_foods,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


def _mock_response(
    *,
    status: int = 200,
    json_body=None,
    text: str = "",
    content_type: str = "application/json",
    remote_ip: str | None = "56.136.221.163",
):
    """Build a mock response that satisfies the new client's
    expectations: status, headers.get('content-type'), .json(),
    .text, .content, and remote_ip via raw._connection.sock."""
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"content-type": content_type}
    if json_body is not None:
        resp.json.return_value = json_body
        resp.text = json.dumps(json_body)
        resp.content = resp.text.encode()
    else:
        resp.json.side_effect = ValueError("not json")
        resp.text = text
        resp.content = text.encode()
    if remote_ip is not None:
        resp.raw._connection.sock.getpeername.return_value = (remote_ip, 443)
    else:
        resp.raw._connection.sock.getpeername.side_effect = AttributeError
    return resp


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def reset_health():
    reset_ip_health()
    yield
    reset_ip_health()


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch):
    """Override tenacity's wait to zero so the test suite doesn't take
    minutes burning backoff. The fixture neutralises wait_exponential
    by replacing the wait callable on the decorated function."""
    from ..usda import client as client_mod
    # The retry decorator's `retry` instance is at _get_json.retry.
    client_mod._get_json.retry.wait = lambda *a, **kw: 0


# ───────────────────────────────────────────────────────────────────────
# Existing behavior preserved
# ───────────────────────────────────────────────────────────────────────


class TestSearchFoods:
    @patch("src.core.usda.client._session.get")
    def test_search_returns_foods(self, mock_get):
        mock_get.return_value = _mock_response(
            json_body=_load_fixture("search_chicken.json"),
        )
        results = search_foods("chicken breast")
        assert len(results) == 3
        assert results[0].fdc_id == 171077
        assert (
            results[0].description
            == "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw"
        )
        assert results[0].food_category == "Poultry Products"
        assert len(results[0].nutrients) > 0

    def test_search_empty_query_raises(self):
        with pytest.raises(ValueError, match="empty"):
            search_foods("")

    @patch("src.core.usda.client._session.get")
    def test_search_no_results(self, mock_get):
        mock_get.return_value = _mock_response(
            json_body=_load_fixture("search_empty.json"),
        )
        results = search_foods("xyznonexistent")
        assert results == []

    @patch("src.core.usda.client._session.get")
    def test_search_5xx_raises_transient_after_retries(self, mock_get):
        mock_get.return_value = _mock_response(
            status=500,
            text='{"error":"server"}',
            content_type="application/json",
        )
        with pytest.raises(UsdaTransientError, match="500"):
            search_foods("chicken")
        # Tenacity retries 3 times on transient.
        assert mock_get.call_count == 3

    @patch("src.core.usda.client._session.get")
    def test_search_rate_limited_raises(self, mock_get):
        mock_get.return_value = _mock_response(
            status=429,
            json_body={"error": "rate limit"},
        )
        with pytest.raises(UsdaRateLimitError):
            search_foods("chicken")
        # 429 is not retried internally.
        assert mock_get.call_count == 1

    @patch("src.core.usda.client._session.get")
    def test_get_food_returns_detail(self, mock_get):
        mock_get.return_value = _mock_response(
            json_body=_load_fixture("food_171077.json"),
        )
        detail = get_food(171077)
        assert detail.fdc_id == 171077
        assert (
            detail.description
            == "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw"
        )
        assert detail.food_category == "Poultry Products"
        assert len(detail.nutrients) > 0
        protein = [n for n in detail.nutrients if n.number == 203][0]
        assert protein.value == 22.5

    @patch("src.core.usda.client._session.get")
    def test_get_food_json_404_raises_not_found_immediately(self, mock_get):
        """A proper JSON 404 from USDA is terminal — the resource really
        doesn't exist. No retry, immediate UsdaFoodNotFoundError."""
        mock_get.return_value = _mock_response(
            status=404,
            json_body={"error": {"code": "NOT_FOUND"}},
        )
        with pytest.raises(UsdaFoodNotFoundError):
            get_food(999999)
        # Critically: NOT retried, because a real 404 isn't transient.
        assert mock_get.call_count == 1

    @patch("src.core.usda.client._session.get")
    def test_search_includes_all_data_types(self, mock_get):
        fixture = _load_fixture("search_chicken.json")
        fixture["foods"].append({
            "fdcId": 999999,
            "description": "SR Legacy food",
            "dataType": "SR Legacy",
            "foodCategory": "Other",
            "foodNutrients": [],
        })
        mock_get.return_value = _mock_response(json_body=fixture)
        results = search_foods("chicken")
        assert len(results) == 4
        assert any(r.fdc_id == 999999 for r in results)

    @patch("src.core.usda.client._session.get")
    def test_search_sorted_by_nutrient_count_desc(self, mock_get):
        fixture = {
            "foods": [
                {"fdcId": 1, "description": "Few nutrients", "dataType": "Foundation", "foodCategory": "", "foodNutrients": [
                    {"nutrientNumber": "203", "nutrientName": "Protein", "value": 20, "unitName": "g"},
                ]},
                {"fdcId": 2, "description": "Many nutrients", "dataType": "SR Legacy", "foodCategory": "", "foodNutrients": [
                    {"nutrientNumber": "203", "nutrientName": "Protein", "value": 20, "unitName": "g"},
                    {"nutrientNumber": "204", "nutrientName": "Fat", "value": 5, "unitName": "g"},
                    {"nutrientNumber": "205", "nutrientName": "Carbs", "value": 0, "unitName": "g"},
                ]},
            ]
        }
        mock_get.return_value = _mock_response(json_body=fixture)
        results = search_foods("test")
        assert results[0].fdc_id == 2
        assert results[1].fdc_id == 1


# ───────────────────────────────────────────────────────────────────────
# New: layered defense against misrouted-edge / multi-IP DNS LB
# ───────────────────────────────────────────────────────────────────────


class TestMisroutedEdgeDefense:
    """The real failure mode: api.nal.usda.gov is DNS-round-robin'd
    across two edges, and one of them serves the FoodData Central
    marketing HTML page with HTTP 404 for /fdc/v1/* paths. The client
    must (1) recognise this as transient, (2) retry, (3) track the
    bad IP, (4) drain the connection pool on quarantine so the next
    request lands on the other edge."""

    @patch("src.core.usda.client._session.get")
    def test_html_404_is_transient_and_retried(self, mock_get):
        """HTML body with 404 = misrouted edge, NOT real not-found."""
        bad_resp = _mock_response(
            status=404,
            text="<!DOCTYPE html><html><title>USDA FoodData Central</title>",
            content_type="text/html",
            remote_ip="15.200.48.244",
        )
        good_resp = _mock_response(
            json_body=_load_fixture("search_chicken.json"),
            remote_ip="56.136.221.163",
        )
        mock_get.side_effect = [bad_resp, good_resp]

        results = search_foods("chicken")
        assert len(results) == 3
        assert mock_get.call_count == 2  # retried once, succeeded

    @patch("src.core.usda.client._session.get")
    def test_html_404_persisting_through_retries_raises_transient(self, mock_get):
        """If every retry attempt also hits HTML 404, we surface
        UsdaTransientError to the caller — not silent."""
        mock_get.return_value = _mock_response(
            status=404,
            text="<!DOCTYPE html>" + "x" * 200,
            content_type="text/html",
            remote_ip="15.200.48.244",
        )
        with pytest.raises(UsdaTransientError) as excinfo:
            search_foods("chicken")
        assert excinfo.value.remote_ip == "15.200.48.244"
        assert "15.200.48.244" in str(excinfo.value)
        assert mock_get.call_count == 3  # tenacity stop_after_attempt(3)

    @patch("src.core.usda.client._session.get")
    def test_html_200_also_transient(self, mock_get):
        """A 'successful' status with HTML body is still wrong-shape
        and should retry, not silently return parsed garbage."""
        mock_get.return_value = _mock_response(
            status=200,
            text="<html>this is not the api response</html>",
            content_type="text/html",
            remote_ip="15.200.48.244",
        )
        with pytest.raises(UsdaTransientError):
            search_foods("chicken")

    @patch("src.core.usda.client._session.get")
    def test_quarantine_after_three_consecutive_failures(self, mock_get):
        """Three consecutive transient failures from the same IP →
        quarantined → pool drained on the third failure."""
        mock_get.return_value = _mock_response(
            status=404,
            text="<html>misrouted</html>",
            content_type="text/html",
            remote_ip="15.200.48.244",
        )
        with pytest.raises(UsdaTransientError):
            search_foods("chicken")
        snapshot = ip_health_snapshot()
        assert "15.200.48.244" in snapshot
        assert snapshot["15.200.48.244"]["quarantined"] is True
        assert snapshot["15.200.48.244"]["consecutive_failures"] >= 3

    @patch("src.core.usda.client._session.get")
    def test_success_resets_consecutive_failures(self, mock_get):
        """A success after a single failure resets the consecutive
        counter — only sustained failures quarantine."""
        bad = _mock_response(
            status=404,
            text="<html>bad</html>",
            content_type="text/html",
            remote_ip="15.200.48.244",
        )
        good = _mock_response(
            json_body=_load_fixture("search_chicken.json"),
            remote_ip="15.200.48.244",
        )
        mock_get.side_effect = [bad, good]
        search_foods("chicken")
        snapshot = ip_health_snapshot()
        assert snapshot["15.200.48.244"]["successes"] == 1
        assert snapshot["15.200.48.244"]["failures"] == 1
        assert snapshot["15.200.48.244"]["consecutive_failures"] == 0
        assert snapshot["15.200.48.244"]["quarantined"] is False


# ───────────────────────────────────────────────────────────────────────
# Transport-level failures
# ───────────────────────────────────────────────────────────────────────


class TestTransportFailures:
    @patch("src.core.usda.client._session.get")
    def test_timeout_treated_as_transient(self, mock_get):
        import requests as requests_lib
        mock_get.side_effect = requests_lib.exceptions.ReadTimeout("timed out")
        with pytest.raises(UsdaTransientError, match="ReadTimeout"):
            search_foods("chicken")
        assert mock_get.call_count == 3  # retried

    @patch("src.core.usda.client._session.get")
    def test_connection_error_treated_as_transient(self, mock_get):
        import requests as requests_lib
        mock_get.side_effect = requests_lib.exceptions.ConnectionError("refused")
        with pytest.raises(UsdaTransientError, match="ConnectionError"):
            search_foods("chicken")
        assert mock_get.call_count == 3

    @patch("src.core.usda.client._session.get")
    def test_malformed_json_response_is_transient(self, mock_get):
        """Content-Type says JSON but body isn't parseable → transient."""
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/json"}
        resp.text = "not actually json"
        resp.content = b"not actually json"
        resp.json.side_effect = ValueError("bad json")
        resp.raw._connection.sock.getpeername.return_value = (
            "56.136.221.163", 443,
        )
        mock_get.return_value = resp
        with pytest.raises(UsdaTransientError, match="malformed JSON"):
            search_foods("chicken")


# ───────────────────────────────────────────────────────────────────────
# Config + non-transient errors
# ───────────────────────────────────────────────────────────────────────


class TestConfigAndOtherErrors:
    def test_missing_api_key_fails_fast(self, monkeypatch):
        """API key not configured → UsdaConfigError, no HTTP call."""
        monkeypatch.delenv("USDA_API_KEY", raising=False)
        with pytest.raises(UsdaConfigError):
            search_foods("chicken")

    def test_empty_api_key_fails_fast(self, monkeypatch):
        monkeypatch.setenv("USDA_API_KEY", "   ")
        with pytest.raises(UsdaConfigError):
            search_foods("chicken")

    @patch("src.core.usda.client._session.get")
    def test_400_bad_request_is_not_transient(self, mock_get):
        """A 4xx (non-404, non-429) is the caller's fault, not
        transient — surface immediately."""
        mock_get.return_value = _mock_response(
            status=400,
            json_body={"error": "bad query"},
        )
        with pytest.raises(UsdaApiError, match="400"):
            search_foods("chicken")
        assert mock_get.call_count == 1  # not retried

    @patch("src.core.usda.client._session.get")
    def test_401_unauthorized_is_not_transient(self, mock_get):
        mock_get.return_value = _mock_response(
            status=401,
            json_body={"error": "bad key"},
        )
        with pytest.raises(UsdaApiError, match="401"):
            search_foods("chicken")
        assert mock_get.call_count == 1


# ───────────────────────────────────────────────────────────────────────
# Observability surface
# ───────────────────────────────────────────────────────────────────────


class TestHealthSnapshot:
    @patch("src.core.usda.client._session.get")
    def test_snapshot_aggregates_per_ip(self, mock_get):
        """Multiple calls hitting different IPs aggregate separately —
        operators can see "edge A: 47 OK, edge B: 23 failures"."""
        mock_get.side_effect = [
            _mock_response(json_body=_load_fixture("search_empty.json"), remote_ip="A"),
            _mock_response(json_body=_load_fixture("search_empty.json"), remote_ip="A"),
            _mock_response(json_body=_load_fixture("search_empty.json"), remote_ip="B"),
        ]
        search_foods("x")
        search_foods("y")
        search_foods("z")
        snapshot = ip_health_snapshot()
        assert snapshot["A"]["successes"] == 2
        assert snapshot["B"]["successes"] == 1
        assert snapshot["A"]["failures"] == 0
        assert snapshot["B"]["failures"] == 0

    @patch("src.core.usda.client._session.get")
    def test_unknown_ip_bucket_when_introspection_fails(self, mock_get):
        """When we can't resolve the remote IP (urllib3 internals
        changed, mocked response, etc.), failures still count — bucketed
        under 'unknown' so they're visible in /health."""
        mock_get.return_value = _mock_response(
            json_body=_load_fixture("search_chicken.json"),
            remote_ip=None,
        )
        search_foods("chicken")
        snapshot = ip_health_snapshot()
        assert "unknown" in snapshot
        assert snapshot["unknown"]["successes"] == 1
