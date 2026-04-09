from ...core.own.nutrient_map.create import create_mapping as core_create
from ...core.ref.admin.nutrients import invalidate_cache


def create_mapping(usda_number: int, usda_name: str, nutrient_name: str):
    status = core_create(usda_number, usda_name, nutrient_name)
    if status:
        invalidate_cache()
    return status
