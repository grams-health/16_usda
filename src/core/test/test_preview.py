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
        assert protein["nutrient_id"] == 1
        assert protein["quantity"] == pytest.approx(0.225)
        # Every entry in `nutrients[]` is by construction mapped + present
        # in the USDA detail — `available` must reflect that. Consumers
        # rely on this per-entry boolean (issue #6).
        assert protein["available"] is True
        for entry in result["nutrients"]:
            assert entry["available"] is True

    @patch("src.core.own.preview.get_nutrient_map")
    @patch("src.core.own.preview.get_food")
    def test_preview_missing_nutrients(self, mock_get_food, mock_nmap):
        # Only map protein -- all others should be missing
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = {203: 1}

        result = preview_usda_food(171077)
        # Only mappable + present nutrients appear in `nutrients[]`.
        assert len(result["nutrients"]) == 1
        assert result["nutrients"][0]["nutrient_id"] == 1
        assert result["coverage"]["available"] == 1

    @patch("src.core.own.preview.get_nutrient_map")
    @patch("src.core.own.preview.get_food")
    def test_preview_aggregates_bundled_amino_pairs(self, mock_get_food, mock_nmap):
        """When USDA Met (#506) and Cys (#507) both map to the same admin
        nutrient_id (id 10 = "Methionine + Cysteine"), the preview must
        return a single aggregated entry whose quantity is the sum, not
        two separate rows. Same for Phe (#508) + Tyr (#509) -> id 11.
        Mirrors the FAO/WHO-style bundled-pair convention enforced in
        transform.py for the import path.
        """
        mock_get_food.return_value = _make_food_detail()
        # Bundled mapping: Met+Cys both -> 10, Phe+Tyr both -> 11
        bundled_map = {
            203: 1, 204: 2, 205: 3, 208: 4, 209: 6, 269: 7, 291: 5,
            512: 6, 503: 7, 504: 8, 505: 9,
            506: 10, 507: 10,  # Methionine + Cystine -> id 10
            508: 11, 509: 11,  # Phenylalanine + Tyrosine -> id 11
            502: 12, 501: 13, 510: 14,
        }
        mock_nmap.return_value = bundled_map

        result = preview_usda_food(171077)
        nuts = {n["nutrient_id"]: n for n in result["nutrients"]}

        # Each bundled id appears exactly once
        amino_ids = [n["nutrient_id"] for n in result["nutrients"]]
        assert amino_ids.count(10) == 1
        assert amino_ids.count(11) == 1

        # Fixture food_171077.json has Met=0.60, Cys=0.24 per 100g.
        # Sum / 100 = 0.0084.
        assert nuts[10]["quantity"] == pytest.approx(0.0084, rel=1e-3)
        # Fixture has Phe=0.88, Tyr=0.75 per 100g. Sum / 100 = 0.0163.
        assert nuts[11]["quantity"] == pytest.approx(0.0163, rel=1e-3)

        # The summed_from field carries both amino names for transparency.
        assert "summed_from" in nuts[10]
        assert set(nuts[10]["summed_from"]) == {"Methionine", "Cystine"}
        assert set(nuts[11]["summed_from"]) == {"Phenylalanine", "Tyrosine"}
