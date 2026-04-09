from ..core.own.import_food import import_usda_food as core_import


def import_usda_food(fdc_id: int):
    return core_import(fdc_id)
