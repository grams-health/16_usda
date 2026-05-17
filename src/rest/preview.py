from flask import jsonify

from ..core.usda.client import (
    UsdaApiError,
    UsdaConfigError,
    UsdaFoodNotFoundError,
    UsdaRateLimitError,
    UsdaTransientError,
)
from ..service.preview import preview_usda_food


def handle_preview(fdc_id):
    try:
        result = preview_usda_food(fdc_id)
        return jsonify(result), 200
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
