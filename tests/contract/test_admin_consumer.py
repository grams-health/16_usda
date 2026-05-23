import os
import pytest
from unittest.mock import patch
from pact import Pact, match


@pytest.fixture
def pact():
    p = Pact("16_usda", "0_admin").with_specification("V4")
    yield p
    p.write_file("pacts")


def _setup_nutrient_map_db():
    """Initialize an in-memory SQLite DB with a test nutrient mapping."""
    from src.core.database import init_db, Base, get_engine, get_session
    from src.core.own.nutrient_map.db import NutrientMapRow

    init_db("sqlite:///:memory:")
    Base.metadata.create_all(get_engine())
    session = get_session()
    try:
        session.add(NutrientMapRow(
            usda_number=203,
            usda_name="Protein",
            nutrient_name="Protein",
        ))
        session.commit()
    finally:
        session.close()


class TestGetNutrientMap:

    def test_get_nutrient_map(self, pact):
        (
            pact
            .upon_receiving("a request to list all nutrients")
            .given("nutrients exist in admin")
            .with_request("GET", "/nutrients")
            .will_respond_with(200)
            .with_body(match.each_like({
                "nutrient_id": match.int(1),
                "nutrient_name": match.str("Protein"),
                "category_id": match.int(1),
            }), content_type="application/json")
        )

        with pact.serve() as srv:
            _setup_nutrient_map_db()
            from src.core.ref.admin.nutrients import invalidate_cache
            invalidate_cache()

            with patch.dict(os.environ, {"ADMIN_SERVICE_URL": str(srv.url).rstrip("/")}):
                from src.core.ref.admin.nutrients import get_nutrient_map
                result = get_nutrient_map()

        assert isinstance(result, dict)
        assert 203 in result
        assert result[203] == 1


class TestCreateFoodWithNutrients:

    def test_create_food_with_nutrients(self, pact):
        (
            pact
            .upon_receiving("a request to create a food with nutrients")
            .given("admin database is initialized")
            .with_request("POST", "/foods/with-nutrients")
            .with_header("Content-Type", "application/json")
            .with_body({
                "food_name": "Chicken Breast",
                "nutrients": [
                    {"nutrient_id": 1, "quantity": 0.225},
                ],
            }, content_type="application/json")
            .will_respond_with(201)
            .with_body({
                "status": "success",
                "message": match.str("Food created with 1 nutrients"),
                "data": {"food_id": match.int(1)},
            }, content_type="application/json")
        )

        with pact.serve() as srv:
            with patch.dict(os.environ, {"ADMIN_SERVICE_URL": str(srv.url).rstrip("/")}):
                from src.core.ref.admin.create_food import create_food_with_nutrients
                result = create_food_with_nutrients(
                    food_name="Chicken Breast",
                    nutrients=[{"nutrient_id": 1, "quantity": 0.225}],
                )

        assert result["status"] == "success"
        assert "data" in result
        assert "food_id" in result["data"]

    def test_create_food_with_nutrients_duplicate_returns_conflict(self, pact):
        """Admin returns 409 when food_name already exists; consumer
        translates this into AdminFoodConflictError so the REST handler
        can map duplicate-import to a 409 response instead of a 5xx."""
        from src.core.ref.admin.create_food import (
            create_food_with_nutrients,
            AdminFoodConflictError,
        )

        (
            pact
            .upon_receiving("a request to create a food with a duplicate name")
            .given("a food named 'Chicken Breast' already exists in admin")
            .with_request("POST", "/foods/with-nutrients")
            .with_header("Content-Type", "application/json")
            .with_body({
                "food_name": "Chicken Breast",
                "nutrients": [
                    {"nutrient_id": 1, "quantity": 0.225},
                ],
            }, content_type="application/json")
            .will_respond_with(409)
            .with_body({
                "status": "error",
                "message": match.str("Food 'Chicken Breast' already exists"),
            }, content_type="application/json")
        )

        with pact.serve() as srv:
            with patch.dict(os.environ, {"ADMIN_SERVICE_URL": str(srv.url).rstrip("/")}):
                with pytest.raises(AdminFoodConflictError) as ctx:
                    create_food_with_nutrients(
                        food_name="Chicken Breast",
                        nutrients=[{"nutrient_id": 1, "quantity": 0.225}],
                    )

        assert ctx.value.food_name == "Chicken Breast"

    def test_create_food_with_nutrients_includes_discrete_unit(self, pact):
        """USDA foodPortions provides a discrete serving (e.g. a medium apple
        at 182g). When present, the import forwards discrete_unit_name +
        grams_per_discrete_unit so the grocery list can render a count hint
        next to the weight (≈ 6 apples)."""
        (
            pact
            .upon_receiving("a request to create a food with discrete display units")
            .given("admin database is initialized")
            .with_request("POST", "/foods/with-nutrients")
            .with_header("Content-Type", "application/json")
            .with_body({
                "food_name": "Apple",
                "nutrients": [
                    {"nutrient_id": 1, "quantity": 0.005},
                ],
                "discrete_unit_name": "medium",
                "grams_per_discrete_unit": 182,
            }, content_type="application/json")
            .will_respond_with(201)
            .with_body({
                "status": "success",
                "message": match.str("Food created with 1 nutrients"),
                "data": {"food_id": match.int(1)},
            }, content_type="application/json")
        )

        with pact.serve() as srv:
            with patch.dict(os.environ, {"ADMIN_SERVICE_URL": str(srv.url).rstrip("/")}):
                from src.core.ref.admin.create_food import create_food_with_nutrients
                result = create_food_with_nutrients(
                    food_name="Apple",
                    nutrients=[{"nutrient_id": 1, "quantity": 0.005}],
                    discrete_unit_name="medium",
                    grams_per_discrete_unit=182,
                )

        assert result["status"] == "success"
