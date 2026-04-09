from flask import jsonify
from ..service.import_food import import_usda_food
from ..core.usda.client import UsdaFoodNotFoundError, UsdaRateLimitError


def handle_import(fdc_id):
    try:
        status = import_usda_food(fdc_id)
        if status:
            response = {
                "status": status.status,
                "message": status.message,
            }
            if status.data:
                response["data"] = status.data
            return jsonify(response), 201
        return jsonify({"status": status.status, "message": status.message}), 409
    except UsdaFoodNotFoundError:
        return jsonify({"status": "error", "message": f"USDA food {fdc_id} not found"}), 404
    except UsdaRateLimitError:
        return jsonify({"status": "error", "message": "USDA API rate limit exceeded"}), 429
