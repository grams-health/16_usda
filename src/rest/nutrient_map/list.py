from flask import jsonify
from ...service.nutrient_map.list import list_mappings, get_mapping


def handle_list_mappings():
    mappings = list_mappings()
    return jsonify([
        {
            "usda_number": m.usda_number,
            "usda_name": m.usda_name,
            "nutrient_name": m.nutrient_name,
        }
        for m in mappings
    ]), 200


def handle_get_mapping(usda_number):
    mapping = get_mapping(usda_number)
    if mapping is None:
        return jsonify({"status": "error", "message": f"Mapping for USDA #{usda_number} not found"}), 404
    return jsonify({
        "usda_number": mapping.usda_number,
        "usda_name": mapping.usda_name,
        "nutrient_name": mapping.nutrient_name,
    }), 200
