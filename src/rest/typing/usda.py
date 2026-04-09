from dataclasses import dataclass


@dataclass
class UsdaSearchResultResponse:
    fdc_id: int
    description: str
    food_category: str
    imported: bool


@dataclass
class PreviewNutrient:
    nutrient_name: str
    quantity: float
    unit: str
    usda_number: int
    available: bool
    note: str = ""


@dataclass
class CoverageInfo:
    available: int
    total: int
    missing: list


@dataclass
class PreviewResponse:
    fdc_id: int
    food_name: str
    food_category: str
    nutrients: list
    coverage: CoverageInfo
