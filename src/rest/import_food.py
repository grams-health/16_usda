from flask import jsonify

from ..core.usda.client import (
    UsdaApiError,
    UsdaConfigError,
    UsdaFoodNotFoundError,
    UsdaRateLimitError,
    UsdaTransientError,
)
from ..service.import_food import import_usda_food


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
    except UsdaConfigError as exc:
        return jsonify({
            "status": "error",
            "message": "USDA client misconfigured",
            "detail": str(exc),
        }), 503
    except UsdaTransientError as exc:
        body = {"status": "error", "message": "USDA upstream temporarily unavailable"}
        if exc.remote_ip:
            body["upstream_ip"] = exc.remote_ip
        return jsonify(body), 502
    except UsdaApiError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502
