from flask import request, jsonify
from ...service.nutrient_map.create import create_mapping


def handle_create_mapping():
    data = request.get_json(force=True, silent=True) or {}
    usda_number = data.get("usda_number")
    usda_name = data.get("usda_name")
    nutrient_name = data.get("nutrient_name")

    if usda_number is None or not usda_name or not nutrient_name:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    status = create_mapping(int(usda_number), str(usda_name), str(nutrient_name))
    if status:
        return jsonify({"status": status.status, "message": status.message}), 201
    return jsonify({"status": status.status, "message": status.message}), 409
