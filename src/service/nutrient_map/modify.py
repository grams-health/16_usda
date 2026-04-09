from ...core.own.nutrient_map.modify import modify_mapping as core_modify
from ...core.ref.admin.nutrients import invalidate_cache


def modify_mapping(usda_number: int, nutrient_name: str):
    status = core_modify(usda_number, nutrient_name)
    if status:
        invalidate_cache()
    return status
