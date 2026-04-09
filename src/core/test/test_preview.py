import json
import os
import pytest
from unittest.mock import patch, MagicMock
from ..typing.usda import UsdaNutrient, UsdaFoodDetail
from ..own.preview import preview_usda_food


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as f:
        return json.load(f)


def _make_food_detail():
    """Create a UsdaFoodDetail from fixture data."""
    data = _load_fixture("food_171077.json")
    food_category = ""
    if isinstance(data.get("foodCategory"), dict):
        food_category = data["foodCategory"].get("description", "")
    nutrients = []
    for fn in data.get("foodNutrients", []):
        nutrient = fn.get("nutrient", {})
        nutrients.append(UsdaNutrient(
            number=int(nutrient["number"]),
            name=nutrient["name"],
            value=float(fn.get("amount", 0)),
            unit=nutrient.get("unitName", ""),
        ))
    return UsdaFoodDetail(
        fdc_id=data["fdcId"],
        description=data["description"],
        food_category=food_category,
        nutrients=nutrients,
    )


def _make_nutrient_map():
    return {
        203: 1, 204: 2, 205: 3, 208: 4, 209: 6, 269: 7, 291: 5,
        606: 8, 645: 9, 646: 10, 605: 11, 619: 12, 618: 13, 601: 14,
        512: 15, 503: 16, 504: 17, 505: 18, 506: 19, 507: 20,
        508: 21, 509: 22, 502: 23, 501: 24, 510: 25,
        303: 26, 301: 27, 304: 28, 309: 29,
        306: 30, 307: 31, 328: 32, 418: 33, 417: 34,
    }


class TestPreview:
    @patch("src.core.own.preview.get_nutrient_map")
    @patch("src.core.own.preview.get_food")
    def test_preview_returns_food_info(self, mock_get_food, mock_nmap):
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = _make_nutrient_map()

        result = preview_usda_food(171077)

        assert result["fdc_id"] == 171077
        assert result["food_name"] == "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw"
        assert result["food_category"] == "Poultry Products"

    @patch("src.core.own.preview.get_nutrient_map")
    @patch("src.core.own.preview.get_food")
    def test_preview_coverage(self, mock_get_food, mock_nmap):
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = _make_nutrient_map()

        result = preview_usda_food(171077)
        coverage = result["coverage"]

        assert coverage["total"] == 34
        assert coverage["available"] > 0
        assert isinstance(coverage["missing"], list)

    @patch("src.core.own.preview.get_nutrient_map")
    @patch("src.core.own.preview.get_food")
    def test_preview_nutrients_divided_by_100(self, mock_get_food, mock_nmap):
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = _make_nutrient_map()

        result = preview_usda_food(171077)
        protein = [n for n in result["nutrients"] if n["usda_number"] == 203][0]
        assert protein["available"] is True
        assert protein["quantity"] == pytest.approx(0.225)

    @patch("src.core.own.preview.get_nutrient_map")
    @patch("src.core.own.preview.get_food")
    def test_preview_missing_nutrients(self, mock_get_food, mock_nmap):
        # Only map protein -- all others should be missing
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = {203: 1}

        result = preview_usda_food(171077)
        available = [n for n in result["nutrients"] if n["available"]]
        assert len(available) == 1
        assert result["coverage"]["available"] == 1
