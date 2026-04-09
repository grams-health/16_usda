import os
import requests


def create_food_with_nutrients(food_name: str, nutrients: list) -> dict:
    """Calls POST /foods/with-nutrients on admin service.

    nutrients: list of dicts with nutrient_id and quantity keys.
    Returns the response JSON dict.
    """
    admin_url = os.environ.get("ADMIN_SERVICE_URL", "http://localhost:6020")
    payload = {
        "food_name": food_name,
        "nutrients": [{"nutrient_id": n["nutrient_id"], "quantity": n["quantity"]} for n in nutrients],
    }
    resp = requests.post(f"{admin_url}/foods/with-nutrients", json=payload)
    resp.raise_for_status()
    return resp.json()
