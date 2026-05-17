from flask import request, jsonify
from ..service.search import search_usda_foods
from ..core.usda.client import UsdaRateLimitError


def handle_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing or empty q parameter"}), 400

    try:
        results = search_usda_foods(query)
        return jsonify({"results": results}), 200
    except UsdaRateLimitError:
        return jsonify({"status": "error", "message": "USDA API rate limit exceeded"}), 429
