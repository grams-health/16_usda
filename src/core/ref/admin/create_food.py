import os
import requests


class AdminFoodConflictError(Exception):
    """Admin returned 409 (food with that name already exists)."""

    def __init__(self, food_name: str, body: dict | None = None):
        self.food_name = food_name
        self.body = body or {}
        super().__init__(f"Admin food conflict for {food_name!r}: {self.body!r}")


def create_food_with_nutrients(food_name: str, nutrients: list) -> dict:
    """Calls POST /foods/with-nutrients on admin service.

    nutrients: list of dicts with nutrient_id and quantity keys.
    Returns the response JSON dict on 201.

    Translates upstream errors at the service boundary (Anti-Corruption
    Layer): admin's 409 (duplicate food_name) becomes
    AdminFoodConflictError so callers can map it to their own 409 instead
    of leaking a 5xx. Other transport errors still propagate via
    raise_for_status() so genuine server failures aren't silently swallowed.
    """
    admin_url = os.environ.get("ADMIN_SERVICE_URL", "http://localhost:6020")
    payload = {
        "food_name": food_name,
        "nutrients": [{"nutrient_id": n["nutrient_id"], "quantity": n["quantity"]} for n in nutrients],
    }
    resp = requests.post(f"{admin_url}/foods/with-nutrients", json=payload)
    if resp.status_code == 409:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        raise AdminFoodConflictError(food_name, body)
    resp.raise_for_status()
    return resp.json()
