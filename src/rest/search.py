from flask import request, jsonify
from ..service.search import search_usda_foods


def handle_search():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"status": "error", "message": "Missing or empty q parameter"}), 400
        results = search_usda_foods(query)
        return jsonify({"results": results}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": type(e).__name__}), 500
