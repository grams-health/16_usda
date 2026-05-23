from ..typing.status import Status
from ..usda.client import get_food
from ..ref.admin.nutrients import get_nutrient_map
from ..ref.admin.create_food import create_food_with_nutrients, AdminFoodConflictError
from .import_log.list import is_imported  # noqa: F401 — re-exported for callers
from .import_log.create import record_import
from .transform import transform_food


def import_usda_food(fdc_id: int) -> Status:
    """Import a USDA food into admin service.

    Admin is the source of truth for "does this food already exist": if
    admin returns 409 we surface that as a domain error (`Status("error",
    ..., error="duplicate")`) and the REST handler maps it to 409.

    The local `import_log` is informational state used by `/usda/search`
    to flag previously-imported FDC ids — a stale log row (e.g.
    admin-side cleanup outside this service) shouldn't block a fresh
    re-import, so we don't short-circuit on `is_imported()` before
    talking to admin. `record_import` is idempotent against
    IntegrityError, so re-imports update the local log without raising.
    """
    # Fetch USDA food detail
    detail = get_food(fdc_id)

    # Get nutrient mapping
    nutrient_map = get_nutrient_map()

    # Transform
    transformed = transform_food(detail, nutrient_map)

    # Create in admin — translates admin 409 to AdminFoodConflictError
    nutrients_payload = [
        {"nutrient_id": n.nutrient_id, "quantity": n.quantity}
        for n in transformed.nutrients
    ]
    try:
        result = create_food_with_nutrients(
            transformed.food_name,
            nutrients_payload,
            discrete_unit_name=transformed.discrete_unit_name,
            grams_per_discrete_unit=transformed.grams_per_discrete_unit,
        )
    except AdminFoodConflictError:
        # Admin already has this food name — surface as duplicate.
        # Status.__bool__ returns False, REST handler returns 409.
        return Status(
            "error",
            f"Food {transformed.food_name!r} already exists in admin",
            error="duplicate",
        )

    food_id = result.get("data", {}).get("food_id") if isinstance(result.get("data"), dict) else result.get("food_id")
    if food_id is None:
        food_id = result.get("data", {}).get("food_id", 0) if isinstance(result.get("data"), dict) else 0

    # Record import (informational; tolerates IntegrityError on stale rows)
    record_import(fdc_id, food_id, transformed.food_name)

    return Status(
        "success",
        f"Food imported with {len(transformed.nutrients)} nutrients",
        data={"food_id": food_id},
    )
