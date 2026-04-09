from ..typing.transform import TransformedNutrient, TransformedFood
from ..typing.usda import UsdaFoodDetail

USDA_TO_NUTRIENT_NAME = {
    203: "Protein", 204: "Fat", 205: "Carbohydrates", 208: "Calories",
    209: "Starch", 269: "Total Sugars", 291: "Fiber",
    606: "Saturated Fat", 645: "Monounsaturated Fat", 646: "Polyunsaturated Fat",
    605: "Trans Fat", 619: "Omega-3 (ALA)", 618: "Omega-6 (LA)", 601: "Cholesterol",
    512: "Histidine", 503: "Isoleucine", 504: "Leucine", 505: "Lysine",
    506: "Methionine", 507: "Cystine", 508: "Phenylalanine", 509: "Tyrosine",
    502: "Threonine", 501: "Tryptophan", 510: "Valine",
    303: "Iron", 301: "Calcium", 304: "Magnesium", 309: "Zinc",
    306: "Potassium", 307: "Sodium", 328: "Vitamin D", 418: "Vitamin B12", 417: "Folate",
}


def transform_food(detail: UsdaFoodDetail, nutrient_map: dict) -> TransformedFood:
    """Transform USDA food detail to admin food format.

    nutrient_map: {usda_number: admin_nutrient_id}
    All quantities divided by 100 (USDA per 100g -> per gram).
    Carbs = #205 - #291 (if #291 missing, use #205 as-is).
    """
    # Build lookup: usda_number -> value
    usda_values = {}
    for n in detail.nutrients:
        usda_values[n.number] = n.value

    transformed = []

    # Handle carbohydrates specially (#205)
    if 205 in usda_values and 205 in nutrient_map:
        carb_value = usda_values[205]
        fiber_value = usda_values.get(291, 0.0)
        net_carbs = carb_value - fiber_value
        transformed.append(TransformedNutrient(
            nutrient_id=nutrient_map[205],
            quantity=net_carbs / 100,
        ))

    # Process all other nutrients (skip #205, handled above)
    for n in detail.nutrients:
        if n.number == 205:
            continue
        if n.number not in nutrient_map:
            continue
        transformed.append(TransformedNutrient(
            nutrient_id=nutrient_map[n.number],
            quantity=n.value / 100,
        ))

    return TransformedFood(
        food_name=detail.description,
        nutrients=transformed,
    )
