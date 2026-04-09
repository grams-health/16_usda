class UsdaNutrient:
    def __init__(self, number: int, name: str, value: float, unit: str):
        self.number = number
        self.name = name
        self.value = value
        self.unit = unit


class UsdaSearchResult:
    def __init__(self, fdc_id: int, description: str, food_category: str, nutrients: list):
        self.fdc_id = fdc_id
        self.description = description
        self.food_category = food_category
        self.nutrients = nutrients


class UsdaFoodDetail:
    def __init__(self, fdc_id: int, description: str, food_category: str, nutrients: list):
        self.fdc_id = fdc_id
        self.description = description
        self.food_category = food_category
        self.nutrients = nutrients
