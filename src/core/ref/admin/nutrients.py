import os
import requests
from ...own.nutrient_map.list import list_nutrient_mappings

_cache = None


def get_nutrient_map() -> dict:
    """Returns {usda_number: admin_nutrient_id} by matching nutrient_map DB entries to admin nutrients by name."""
    global _cache
    if _cache is not None:
        return _cache

    admin_url = os.environ.get("ADMIN_SERVICE_URL", "http://localhost:6020")
    resp = requests.get(f"{admin_url}/nutrients")
    resp.raise_for_status()
    admin_nutrients = resp.json()

    name_to_id = {}
    for n in admin_nutrients:
        name_to_id[n["nutrient_name"]] = n["nutrient_id"]

    mappings = list_nutrient_mappings()
    result = {}
    for m in mappings:
        if m.nutrient_name in name_to_id:
            result[m.usda_number] = name_to_id[m.nutrient_name]

    _cache = result
    return _cache


def invalidate_cache():
    global _cache
    _cache = None
