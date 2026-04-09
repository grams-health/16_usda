import pytest
from unittest.mock import patch, MagicMock
from ..typing.usda import UsdaNutrient, UsdaFoodDetail
from ..own.import_food import import_usda_food


def _make_food_detail():
    return UsdaFoodDetail(
        fdc_id=171077,
        description="Chicken breast",
        food_category="Poultry",
        nutrients=[
            UsdaNutrient(number=203, name="Protein", value=22.5, unit="G"),
            UsdaNutrient(number=204, name="Fat", value=2.62, unit="G"),
        ],
    )


def _make_nutrient_map():
    return {203: 1, 204: 2}


class TestImportFood:
    @patch("src.core.own.import_food.record_import")
    @patch("src.core.own.import_food.create_food_with_nutrients")
    @patch("src.core.own.import_food.get_nutrient_map")
    @patch("src.core.own.import_food.get_food")
    @patch("src.core.own.import_food.is_imported")
    def test_import_success(self, mock_imported, mock_get_food, mock_nmap, mock_create, mock_record):
        from ..typing.status import Status
        mock_imported.return_value = False
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = _make_nutrient_map()
        mock_create.return_value = {"status": "success", "data": {"food_id": 47}}
        mock_record.return_value = Status("success", "recorded")

        result = import_usda_food(171077)
        assert result
        assert result.status == "success"
        assert "2 nutrients" in result.message
        mock_create.assert_called_once()
        mock_record.assert_called_once()

    @patch("src.core.own.import_food.is_imported")
    def test_import_already_imported(self, mock_imported):
        mock_imported.return_value = True
        result = import_usda_food(171077)
        assert not result
        assert result.status == "error"
        assert "already imported" in result.message

    @patch("src.core.own.import_food.get_food")
    @patch("src.core.own.import_food.is_imported")
    def test_import_food_not_found(self, mock_imported, mock_get_food):
        from ..usda.client import UsdaFoodNotFoundError
        mock_imported.return_value = False
        mock_get_food.side_effect = UsdaFoodNotFoundError("not found")

        with pytest.raises(UsdaFoodNotFoundError):
            import_usda_food(999999)

    @patch("src.core.own.import_food.get_food")
    @patch("src.core.own.import_food.is_imported")
    def test_import_rate_limited(self, mock_imported, mock_get_food):
        from ..usda.client import UsdaRateLimitError
        mock_imported.return_value = False
        mock_get_food.side_effect = UsdaRateLimitError("rate limited")

        with pytest.raises(UsdaRateLimitError):
            import_usda_food(171077)

    @patch("src.core.own.import_food.record_import")
    @patch("src.core.own.import_food.create_food_with_nutrients")
    @patch("src.core.own.import_food.get_nutrient_map")
    @patch("src.core.own.import_food.get_food")
    @patch("src.core.own.import_food.is_imported")
    def test_import_calls_admin_with_correct_payload(self, mock_imported, mock_get_food, mock_nmap, mock_create, mock_record):
        from ..typing.status import Status
        mock_imported.return_value = False
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = _make_nutrient_map()
        mock_create.return_value = {"status": "success", "data": {"food_id": 47}}
        mock_record.return_value = Status("success", "recorded")

        import_usda_food(171077)

        call_args = mock_create.call_args
        food_name = call_args[0][0]
        nutrients = call_args[0][1]
        assert food_name == "Chicken breast"
        assert len(nutrients) == 2
        assert all("nutrient_id" in n and "quantity" in n for n in nutrients)

    @patch("src.core.own.import_food.record_import")
    @patch("src.core.own.import_food.create_food_with_nutrients")
    @patch("src.core.own.import_food.get_nutrient_map")
    @patch("src.core.own.import_food.get_food")
    @patch("src.core.own.import_food.is_imported")
    def test_import_records_in_log(self, mock_imported, mock_get_food, mock_nmap, mock_create, mock_record):
        from ..typing.status import Status
        mock_imported.return_value = False
        mock_get_food.return_value = _make_food_detail()
        mock_nmap.return_value = _make_nutrient_map()
        mock_create.return_value = {"status": "success", "data": {"food_id": 47}}
        mock_record.return_value = Status("success", "recorded")

        import_usda_food(171077)

        mock_record.assert_called_once_with(171077, 47, "Chicken breast")
