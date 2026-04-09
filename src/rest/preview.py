from flask import jsonify
from ..service.preview import preview_usda_food
from ..core.usda.client import UsdaFoodNotFoundError, UsdaRateLimitError


def handle_preview(fdc_id):
    try:
        result = preview_usda_food(fdc_id)
        return jsonify(result), 200
    except UsdaFoodNotFoundError:
        return jsonify({"status": "error", "message": f"USDA food {fdc_id} not found"}), 404
    except UsdaRateLimitError:
        return jsonify({"status": "error", "message": "USDA API rate limit exceeded"}), 429
