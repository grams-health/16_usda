import atexit
import os
import unittest
from unittest.mock import patch

from pact import Consumer, Provider, Like, EachLike

pact = Consumer("16_usda").has_pact_with(
    Provider("0_admin"),
    port=9882,
    pact_dir="pacts",
)
pact.start_service()
atexit.register(pact.stop_service)

MOCK_ADMIN_URL = "http://localhost:9882"


def _setup_nutrient_map_db():
    """Initialize an in-memory SQLite nutrient_map DB with a test mapping."""
    from src.core.own.nutrient_map.db import init_db, get_session, NutrientMapRow

    init_db("sqlite:///:memory:")
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


class TestGetNutrientMap(unittest.TestCase):

    def test_get_nutrient_map(self):
        (
            pact.given("nutrients exist in admin")
            .upon_receiving("a request to list all nutrients")
            .with_request(method="GET", path="/nutrients")
            .will_respond_with(
                status=200,
                body=EachLike({
                    "nutrient_id": Like(1),
                    "nutrient_name": Like("Protein"),
                    "category_id": Like(1),
                }),
            )
        )

        with pact:
            _setup_nutrient_map_db()
            from src.core.ref.admin.nutrients import invalidate_cache
            invalidate_cache()

            with patch.dict(os.environ, {"ADMIN_SERVICE_URL": MOCK_ADMIN_URL}):
                from src.core.ref.admin.nutrients import get_nutrient_map

                result = get_nutrient_map()

        self.assertIsInstance(result, dict)
        self.assertIn(203, result)
        self.assertEqual(result[203], 1)


class TestCreateFoodWithNutrients(unittest.TestCase):

    def test_create_food_with_nutrients(self):
        (
            pact.given("admin database is initialized")
            .upon_receiving("a request to create a food with nutrients")
            .with_request(
                method="POST",
                path="/foods/with-nutrients",
                headers={"Content-Type": "application/json"},
                body={
                    "food_name": "Chicken Breast",
                    "nutrients": [
                        {"nutrient_id": 1, "quantity": 0.225},
                    ],
                },
            )
            .will_respond_with(
                status=201,
                body={
                    "status": "success",
                    "message": Like("Food created with 1 nutrients"),
                    "data": {"food_id": Like(1)},
                },
            )
        )

        with pact:
            with patch.dict(os.environ, {"ADMIN_SERVICE_URL": MOCK_ADMIN_URL}):
                from src.core.ref.admin.create_food import create_food_with_nutrients

                result = create_food_with_nutrients(
                    food_name="Chicken Breast",
                    nutrients=[{"nutrient_id": 1, "quantity": 0.225}],
                )

        self.assertEqual(result["status"], "success")
        self.assertIn("data", result)
        self.assertIn("food_id", result["data"])
