from ..core.own.preview import preview_usda_food as core_preview


def preview_usda_food(fdc_id: int) -> dict:
    return core_preview(fdc_id)
