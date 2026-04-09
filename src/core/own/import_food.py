from ..typing.status import Status
from ..usda.client import get_food
from ..ref.admin.nutrients import get_nutrient_map
from ..ref.admin.create_food import create_food_with_nutrients
from .import_log.list import is_imported
from .import_log.create import record_import
from .transform import transform_food


def import_usda_food(fdc_id: int) -> Status:
    """Import a USDA food into admin service."""
    # Check if already imported
    if is_imported(fdc_id):
        return Status("error", f"Food {fdc_id} already imported")

    # Fetch USDA food detail
    detail = get_food(fdc_id)

    # Get nutrient mapping
    nutrient_map = get_nutrient_map()

    # Transform
    transformed = transform_food(detail, nutrient_map)

    # Create in admin
    nutrients_payload = [
        {"nutrient_id": n.nutrient_id, "quantity": n.quantity}
        for n in transformed.nutrients
    ]
    result = create_food_with_nutrients(transformed.food_name, nutrients_payload)

    food_id = result.get("data", {}).get("food_id") if isinstance(result.get("data"), dict) else result.get("food_id")
    if food_id is None:
        food_id = result.get("data", {}).get("food_id", 0) if isinstance(result.get("data"), dict) else 0

    # Record import
    record_import(fdc_id, food_id, transformed.food_name)

    return Status(
        "success",
        f"Food imported with {len(transformed.nutrients)} nutrients",
        data={"food_id": food_id},
    )
