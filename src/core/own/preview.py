from ..usda.client import get_food
from ..ref.admin.nutrients import get_nutrient_map
from .transform import USDA_TO_NUTRIENT_NAME


def preview_usda_food(fdc_id: int) -> dict:
    """Fetch USDA food detail and map to admin nutrients with coverage info.

    The `nutrients` array contains only nutrients that are both present in
    the USDA detail AND mappable via the nutrient_map — every entry has a
    real `nutrient_id` and a numeric `quantity`. Unmappable / absent
    nutrients are reported in `coverage.missing` rather than as null
    placeholders inside `nutrients`, so the response satisfies the
    consumer-driven Pact (which forbids null `quantity` and demands
    integer `nutrient_id`).
    """
    detail = get_food(fdc_id)
    nutrient_map = get_nutrient_map()

    # Build lookup: usda_number -> value, unit from the detail
    usda_values = {}
    usda_units = {}
    for n in detail.nutrients:
        usda_values[n.number] = n.value
        usda_units[n.number] = n.unit

    nutrients = []
    missing = []

    for usda_number, nutrient_name in USDA_TO_NUTRIENT_NAME.items():
        if usda_number in usda_values and usda_number in nutrient_map:
            value = usda_values[usda_number]
            unit = usda_units[usda_number]

            entry = {
                "nutrient_id": nutrient_map[usda_number],
                "nutrient_name": nutrient_name,
                "quantity": value / 100,
                "unit": unit,
                "usda_number": usda_number,
            }

            # Special note for carbohydrates
            if usda_number == 205:
                fiber_value = usda_values.get(291, 0.0)
                entry["quantity"] = (value - fiber_value) / 100
                entry["note"] = "computed: #205 - #291"

            nutrients.append(entry)
        else:
            missing.append(nutrient_name)

    return {
        "fdc_id": detail.fdc_id,
        "food_name": detail.description,
        "food_category": detail.food_category,
        "nutrients": nutrients,
        "coverage": {
            "available": len(nutrients),
            "total": len(USDA_TO_NUTRIENT_NAME),
            "missing": missing,
        },
    }
