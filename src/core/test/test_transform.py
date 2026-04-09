import pytest
from ..typing.usda import UsdaNutrient, UsdaFoodDetail
from ..own.transform import transform_food


def _make_detail(nutrients_data):
    nutrients = [
        UsdaNutrient(number=n[0], name=n[1], value=n[2], unit=n[3])
        for n in nutrients_data
    ]
    return UsdaFoodDetail(
        fdc_id=171077,
        description="Test Food",
        food_category="Test",
        nutrients=nutrients,
    )


def _make_nutrient_map():
    """Standard nutrient_map: {usda_number: admin_nutrient_id}."""
    return {
        203: 1, 204: 2, 205: 3, 208: 4, 209: 6, 269: 7, 291: 5,
        606: 8, 645: 9, 646: 10, 605: 11, 619: 12, 618: 13, 601: 14,
        512: 15, 503: 16, 504: 17, 505: 18, 506: 19, 507: 20,
        508: 21, 509: 22, 502: 23, 501: 24, 510: 25,
        303: 26, 301: 27, 304: 28, 309: 29,
        306: 30, 307: 31, 328: 32, 418: 33, 417: 34,
    }


class TestTransform:
    def test_basic_transform(self):
        detail = _make_detail([
            (203, "Protein", 22.5, "G"),
            (204, "Fat", 2.62, "G"),
        ])
        nmap = {203: 1, 204: 2}
        result = transform_food(detail, nmap)
        assert result.food_name == "Test Food"
        assert len(result.nutrients) == 2

    def test_quantities_divided_by_100(self):
        detail = _make_detail([(203, "Protein", 22.5, "G")])
        nmap = {203: 1}
        result = transform_food(detail, nmap)
        assert result.nutrients[0].quantity == pytest.approx(0.225)

    def test_carbs_minus_fiber(self):
        detail = _make_detail([
            (205, "Carbs", 10.0, "G"),
            (291, "Fiber", 3.0, "G"),
        ])
        nmap = {205: 3, 291: 5}
        result = transform_food(detail, nmap)
        # Carbs entry: (10 - 3) / 100 = 0.07
        carb_nutrients = [n for n in result.nutrients if n.nutrient_id == 3]
        assert len(carb_nutrients) == 1
        assert carb_nutrients[0].quantity == pytest.approx(0.07)

    def test_carbs_without_fiber(self):
        detail = _make_detail([
            (205, "Carbs", 10.0, "G"),
        ])
        nmap = {205: 3}
        result = transform_food(detail, nmap)
        carb_nutrients = [n for n in result.nutrients if n.nutrient_id == 3]
        assert len(carb_nutrients) == 1
        assert carb_nutrients[0].quantity == pytest.approx(0.10)

    def test_zero_values_included(self):
        detail = _make_detail([
            (605, "Trans fat", 0.0, "G"),
        ])
        nmap = {605: 11}
        result = transform_food(detail, nmap)
        assert len(result.nutrients) == 1
        assert result.nutrients[0].quantity == 0.0

    def test_unmapped_nutrients_skipped(self):
        detail = _make_detail([
            (203, "Protein", 22.5, "G"),
            (999, "Unknown", 1.0, "G"),
        ])
        nmap = {203: 1}
        result = transform_food(detail, nmap)
        assert len(result.nutrients) == 1

    def test_methionine_cystine_individual(self):
        detail = _make_detail([
            (506, "Methionine", 0.60, "G"),
            (507, "Cystine", 0.24, "G"),
        ])
        nmap = {506: 19, 507: 20}
        result = transform_food(detail, nmap)
        assert len(result.nutrients) == 2
        met = [n for n in result.nutrients if n.nutrient_id == 19][0]
        cys = [n for n in result.nutrients if n.nutrient_id == 20][0]
        assert met.quantity == pytest.approx(0.006)
        assert cys.quantity == pytest.approx(0.0024)

    def test_phenylalanine_tyrosine_individual(self):
        detail = _make_detail([
            (508, "Phenylalanine", 0.88, "G"),
            (509, "Tyrosine", 0.75, "G"),
        ])
        nmap = {508: 21, 509: 22}
        result = transform_food(detail, nmap)
        assert len(result.nutrients) == 2

    def test_full_chicken_transform(self):
        detail = _make_detail([
            (203, "Protein", 22.5, "G"),
            (204, "Fat", 2.62, "G"),
            (205, "Carbs", 0.0, "G"),
            (208, "Energy", 114.0, "KCAL"),
            (291, "Fiber", 0.0, "G"),
            (606, "Sat fat", 0.56, "G"),
            (504, "Leucine", 1.73, "G"),
        ])
        nmap = _make_nutrient_map()
        result = transform_food(detail, nmap)
        # Should have: Protein, Fat, Carbs(computed), Calories, Fiber, Sat Fat, Leucine = 7
        assert len(result.nutrients) == 7

    def test_empty_nutrients(self):
        detail = _make_detail([])
        nmap = {203: 1}
        result = transform_food(detail, nmap)
        assert len(result.nutrients) == 0
