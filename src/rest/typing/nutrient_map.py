from dataclasses import dataclass


@dataclass
class NutrientMapping:
    usda_number: int
    usda_name: str
    nutrient_name: str
