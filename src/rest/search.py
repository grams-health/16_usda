import logging

from flask import request, jsonify
from ..service.search import search_usda_foods
from ..core.usda.client import UsdaRateLimitError

logger = logging.getLogger(__name__)


def handle_search():
    try:
        try:
            query = request.args.get("q", "").strip()
            if not query:
                return jsonify({"status": "error", "message": "Missing or empty q parameter"}), 400
            results = search_usda_foods(query)
            return jsonify({"results": results}), 200
        finally:
            pass
    except UsdaRateLimitError:
        try:
            return jsonify({"status": "error", "message": "USDA API rate limit exceeded"}), 429
        except Exception:
            return (
                '{"status": "error", "message": "USDA API rate limit exceeded"}',
                429,
                {"Content-Type": "application/json"},
            )
    except Exception:
        try:
            logger.exception("Unhandled exception in search view")
        except Exception:
            pass
        try:
            return jsonify({"status": "error", "message": "Internal server error"}), 503
        except Exception:
            return (
                '{"status": "error", "message": "Internal server error"}',
                503,
                {"Content-Type": "application/json"},
            )
