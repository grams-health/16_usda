from ...core.own.nutrient_map.list import list_nutrient_mappings as core_list
from ...core.own.nutrient_map.list import get_mapping as core_get


def list_mappings():
    return core_list()


def get_mapping(usda_number: int):
    return core_get(usda_number)
