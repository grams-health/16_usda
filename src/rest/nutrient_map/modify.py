from flask import request, jsonify
from ...service.nutrient_map.modify import modify_mapping


def handle_modify_mapping(usda_number):
    data = request.get_json(force=True, silent=True) or {}
    nutrient_name = data.get("nutrient_name")

    if not nutrient_name:
        return jsonify({"status": "error", "message": "Missing required field: nutrient_name"}), 400

    status = modify_mapping(usda_number, str(nutrient_name))
    if status:
        return jsonify({"status": status.status, "message": status.message}), 200
    return jsonify({"status": status.status, "message": status.message}), 404
