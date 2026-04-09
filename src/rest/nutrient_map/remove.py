from flask import jsonify
from ...service.nutrient_map.remove import remove_mapping


def handle_remove_mapping(usda_number):
    status = remove_mapping(usda_number)
    if status:
        return jsonify({"status": status.status, "message": status.message}), 200
    return jsonify({"status": status.status, "message": status.message}), 404
