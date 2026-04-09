from ..usda.client import search_foods as usda_search
from .import_log.list import list_imported_fdc_ids


def search_usda_foods(query: str) -> list:
    """Search USDA foods and annotate with imported status."""
    results = usda_search(query)
    imported_ids = list_imported_fdc_ids()

    return [
        {
            "fdc_id": r.fdc_id,
            "description": r.description,
            "food_category": r.food_category,
            "imported": r.fdc_id in imported_ids,
        }
        for r in results
    ]
