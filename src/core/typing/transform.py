class TransformedNutrient:
    def __init__(self, nutrient_id: int, quantity: float):
        self.nutrient_id = nutrient_id
        self.quantity = quantity


class TransformedFood:
    def __init__(
        self,
        food_name: str,
        nutrients: list,
        discrete_unit_name: str | None = None,
        grams_per_discrete_unit: float | None = None,
    ):
        self.food_name = food_name
        self.nutrients = nutrients
        self.discrete_unit_name = discrete_unit_name
        self.grams_per_discrete_unit = grams_per_discrete_unit
