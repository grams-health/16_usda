import json
import os
import pytest
from unittest.mock import patch, MagicMock
from ..usda.client import (
    search_foods,
    get_food,
    UsdaRateLimitError,
    UsdaFoodNotFoundError,
    UsdaApiError,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "test-key")


class TestSearchFoods:
    @patch("src.core.usda.client.requests.get")
    def test_search_returns_foods(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _load_fixture("search_chicken.json")
        mock_get.return_value = mock_resp

        results = search_foods("chicken breast")

        assert len(results) == 3
        assert results[0].fdc_id == 171077
        assert results[0].description == "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw"
        assert results[0].food_category == "Poultry Products"
        assert len(results[0].nutrients) > 0

    def test_search_empty_query_raises(self):
        with pytest.raises(ValueError, match="empty"):
            search_foods("")

    @patch("src.core.usda.client.requests.get")
    def test_search_no_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _load_fixture("search_empty.json")
        mock_get.return_value = mock_resp

        results = search_foods("xyznonexistent")
        assert results == []

    @patch("src.core.usda.client.requests.get")
    def test_search_api_error_raises(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        with pytest.raises(UsdaApiError, match="500"):
            search_foods("chicken")

    @patch("src.core.usda.client.requests.get")
    def test_search_rate_limited_raises(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        with pytest.raises(UsdaRateLimitError):
            search_foods("chicken")

    @patch("src.core.usda.client.requests.get")
    def test_get_food_returns_detail(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _load_fixture("food_171077.json")
        mock_get.return_value = mock_resp

        detail = get_food(171077)

        assert detail.fdc_id == 171077
        assert detail.description == "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw"
        assert detail.food_category == "Poultry Products"
        assert len(detail.nutrients) > 0
        protein = [n for n in detail.nutrients if n.number == 203][0]
        assert protein.value == 22.5

    @patch("src.core.usda.client.requests.get")
    def test_get_food_not_found_raises(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        with pytest.raises(UsdaFoodNotFoundError):
            get_food(999999)

    @patch("src.core.usda.client.requests.get")
    def test_search_includes_all_data_types(self, mock_get):
        fixture = _load_fixture("search_chicken.json")
        # Add an SR Legacy food
        fixture["foods"].append({
            "fdcId": 999999,
            "description": "SR Legacy food",
            "dataType": "SR Legacy",
            "foodCategory": "Other",
            "foodNutrients": [],
        })
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fixture
        mock_get.return_value = mock_resp

        results = search_foods("chicken")
        assert len(results) == 4  # Foundation + SR Legacy
        assert any(r.fdc_id == 999999 for r in results)

    @patch("src.core.usda.client.requests.get")
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
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fixture
        mock_get.return_value = mock_resp

        results = search_foods("test")
        assert results[0].fdc_id == 2  # Most nutrients first
        assert results[1].fdc_id == 1
