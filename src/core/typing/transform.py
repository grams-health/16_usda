class TransformedNutrient:
    def __init__(self, nutrient_id: int, quantity: float):
        self.nutrient_id = nutrient_id
        self.quantity = quantity


class TransformedFood:
    def __init__(self, food_name: str, nutrients: list):
        self.food_name = food_name
        self.nutrients = nutrients
