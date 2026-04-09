import pytest
from unittest.mock import patch, MagicMock
from ..typing.usda import UsdaSearchResult
from ..own.search import search_usda_foods


class TestSearch:
    @patch("src.core.own.search.list_imported_fdc_ids")
    @patch("src.core.own.search.usda_search")
    def test_search_returns_results_with_imported_flags(self, mock_usda, mock_imported):
        mock_usda.return_value = [
            UsdaSearchResult(fdc_id=171077, description="Chicken breast", food_category="Poultry", nutrients=[]),
            UsdaSearchResult(fdc_id=171078, description="Chicken thigh", food_category="Poultry", nutrients=[]),
        ]
        mock_imported.return_value = {171077}

        results = search_usda_foods("chicken")

        assert len(results) == 2
        assert results[0]["imported"] is True
        assert results[1]["imported"] is False

    @patch("src.core.own.search.list_imported_fdc_ids")
    @patch("src.core.own.search.usda_search")
    def test_search_empty_results(self, mock_usda, mock_imported):
        mock_usda.return_value = []
        mock_imported.return_value = set()

        results = search_usda_foods("xyznonexistent")
        assert results == []

    @patch("src.core.own.search.list_imported_fdc_ids")
    @patch("src.core.own.search.usda_search")
    def test_search_none_imported(self, mock_usda, mock_imported):
        mock_usda.return_value = [
            UsdaSearchResult(fdc_id=171077, description="Chicken breast", food_category="Poultry", nutrients=[]),
        ]
        mock_imported.return_value = set()

        results = search_usda_foods("chicken")
        assert results[0]["imported"] is False
