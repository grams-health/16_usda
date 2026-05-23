class UsdaNutrient:
    def __init__(self, number: int, name: str, value: float, unit: str):
        self.number = number
        self.name = name
        self.value = value
        self.unit = unit


class UsdaSearchResult:
    def __init__(self, fdc_id: int, description: str, food_category: str, nutrients: list, data_type: str = ""):
        self.fdc_id = fdc_id
        self.description = description
        self.food_category = food_category
        self.nutrients = nutrients
        self.data_type = data_type


class UsdaFoodPortion:
    """One entry from USDA foodPortions: a discrete serving + its gram weight.

    e.g. {"measureUnit": {"name": "medium"}, "gramWeight": 182, "modifier": "medium"}
    Apple → UsdaFoodPortion(unit_name="medium", gram_weight=182.0, modifier="medium").
    """

    def __init__(self, unit_name: str, gram_weight: float, modifier: str = ""):
        self.unit_name = unit_name
        self.gram_weight = gram_weight
        self.modifier = modifier


class UsdaFoodDetail:
    def __init__(self, fdc_id: int, description: str, food_category: str, nutrients: list, portions: list | None = None):
        self.fdc_id = fdc_id
        self.description = description
        self.food_category = food_category
        self.nutrients = nutrients
        self.portions = portions or []
