import os
import requests


class AdminFoodConflictError(Exception):
    """Admin returned 409 (food with that name already exists)."""

    def __init__(self, food_name: str, body: dict | None = None):
        self.food_name = food_name
        self.body = body or {}
        super().__init__(f"Admin food conflict for {food_name!r}: {self.body!r}")


def create_food_with_nutrients(
    food_name: str,
    nutrients: list,
    discrete_unit_name: str | None = None,
    grams_per_discrete_unit: float | None = None,
) -> dict:
    """Calls POST /foods/with-nutrients on admin service.

    nutrients: list of dicts with nutrient_id and quantity keys.
    discrete_unit_name + grams_per_discrete_unit are optional display-unit
    fields surfaced from USDA foodPortions; admin persists them alongside
    the food row. is_liquid and grams_per_ml are NOT auto-set from USDA —
    admin marks liquids manually because USDA category data is too noisy.

    Returns the response JSON dict on 201.

    Translates upstream errors at the service boundary (Anti-Corruption
    Layer): admin's 409 (duplicate food_name) becomes
    AdminFoodConflictError so callers can map it to their own 409 instead
    of leaking a 5xx. Other transport errors still propagate via
    raise_for_status() so genuine server failures aren't silently swallowed.
    """
    admin_url = os.environ.get("ADMIN_SERVICE_URL", "http://localhost:6020")
    payload: dict = {
        "food_name": food_name,
        "nutrients": [{"nutrient_id": n["nutrient_id"], "quantity": n["quantity"]} for n in nutrients],
    }
    if discrete_unit_name is not None and grams_per_discrete_unit is not None:
        payload["discrete_unit_name"] = discrete_unit_name
        payload["grams_per_discrete_unit"] = grams_per_discrete_unit
    resp = requests.post(f"{admin_url}/foods/with-nutrients", json=payload)
    if resp.status_code == 409:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        raise AdminFoodConflictError(food_name, body)
    resp.raise_for_status()
    return resp.json()
