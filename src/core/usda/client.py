import os
import requests
from ..typing.usda import UsdaNutrient, UsdaSearchResult, UsdaFoodDetail


class UsdaApiError(Exception):
    pass


class UsdaRateLimitError(UsdaApiError):
    pass


class UsdaFoodNotFoundError(UsdaApiError):
    pass


USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"


def _get_api_key():
    key = os.environ.get("USDA_API_KEY")
    if not key:
        raise UsdaApiError("USDA_API_KEY environment variable not set")
    return key


def search_foods(query: str, page_size: int = 25) -> list:
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    api_key = _get_api_key()
    url = f"{USDA_BASE_URL}/foods/search"
    params = {
        "api_key": api_key,
        "query": query,
        "dataType": "Foundation",
        "pageSize": page_size,
    }

    resp = requests.get(url, params=params)

    if resp.status_code == 429:
        raise UsdaRateLimitError("USDA API rate limit exceeded")
    if resp.status_code != 200:
        raise UsdaApiError(f"USDA API error: {resp.status_code}")

    data = resp.json()
    foods = data.get("foods", [])

    results = []
    for food in foods:
        if food.get("dataType") != "Foundation":
            continue
        nutrients = []
        for fn in food.get("foodNutrients", []):
            nutrients.append(UsdaNutrient(
                number=int(fn["nutrientNumber"]),
                name=fn["nutrientName"],
                value=float(fn["value"]),
                unit=fn["unitName"],
            ))
        results.append(UsdaSearchResult(
            fdc_id=food["fdcId"],
            description=food["description"],
            food_category=food.get("foodCategory", ""),
            nutrients=nutrients,
        ))

    return results


def get_food(fdc_id: int) -> UsdaFoodDetail:
    api_key = _get_api_key()
    url = f"{USDA_BASE_URL}/food/{fdc_id}"
    params = {"api_key": api_key}

    resp = requests.get(url, params=params)

    if resp.status_code == 429:
        raise UsdaRateLimitError("USDA API rate limit exceeded")
    if resp.status_code == 404:
        raise UsdaFoodNotFoundError(f"USDA food {fdc_id} not found")
    if resp.status_code != 200:
        raise UsdaApiError(f"USDA API error: {resp.status_code}")

    data = resp.json()

    food_category = ""
    if isinstance(data.get("foodCategory"), dict):
        food_category = data["foodCategory"].get("description", "")
    elif isinstance(data.get("foodCategory"), str):
        food_category = data["foodCategory"]

    nutrients = []
    for fn in data.get("foodNutrients", []):
        nutrient = fn.get("nutrient", {})
        nutrients.append(UsdaNutrient(
            number=int(nutrient["number"]),
            name=nutrient["name"],
            value=float(fn.get("amount", 0)),
            unit=nutrient.get("unitName", ""),
        ))

    return UsdaFoodDetail(
        fdc_id=data["fdcId"],
        description=data["description"],
        food_category=food_category,
        nutrients=nutrients,
    )
