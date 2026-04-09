from ..core.own.search import search_usda_foods as core_search


def search_usda_foods(query: str) -> list:
    return core_search(query)
