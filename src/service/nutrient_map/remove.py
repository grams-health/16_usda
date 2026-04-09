from ...core.own.nutrient_map.remove import remove_mapping as core_remove
from ...core.ref.admin.nutrients import invalidate_cache


def remove_mapping(usda_number: int):
    status = core_remove(usda_number)
    if status:
        invalidate_cache()
    return status
