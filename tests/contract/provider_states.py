"""Provider-state setup for Pact verification.

Each `given:` clause from a consumer pact maps to a setup function that
puts the provider into the required state — a combination of seeding
the local SQLite tables (import_log, nutrient_map) and staging canned
USDA / admin responses on the request fakes installed in `conftest`.

Strict mode: every state name a consumer references must have a
registered handler. An unrecognized state returns 500 so the verifier
fails loudly rather than silently passing on an empty DB.
"""
from flask import Blueprint, jsonify, request

from src.core.own.import_log.db import ImportsRow
from src.core.own.nutrient_map.db import NutrientMapRow
from src.core.database import get_session
from src.core.ref.admin.nutrients import invalidate_cache

from tests.contract.conftest import (
    USDA_SEARCH_RESPONSES,
    USDA_FOOD_RESPONSES,
    ADMIN_NUTRIENTS_RESPONSE,
)

provider_states = Blueprint("provider_states", __name__)


# ── Reset helpers ──────────────────────────────────────────────────

def _clear_db():
    """Wipe both owned tables so each state starts from a known baseline."""
    session = get_session()
    try:
        session.query(ImportsRow).delete()
        session.query(NutrientMapRow).delete()
        session.commit()
    finally:
        session.close()


def _reset():
    _clear_db()
    invalidate_cache()
    USDA_SEARCH_RESPONSES.clear()
    USDA_FOOD_RESPONSES.clear()
    # Repopulate the admin nutrients list with the canonical set the
    # consumer pacts assume — Protein at id 1 covers every interaction.
    ADMIN_NUTRIENTS_RESPONSE.clear()
    ADMIN_NUTRIENTS_RESPONSE.extend([
        {"nutrient_id": 1, "nutrient_name": "Protein", "category_id": 1},
    ])


# ── DB seed helpers ────────────────────────────────────────────────

def _seed_nutrient_mapping(usda_number, usda_name, nutrient_name):
    session = get_session()
    try:
        session.merge(NutrientMapRow(
            usda_number=usda_number,
            usda_name=usda_name,
            nutrient_name=nutrient_name,
        ))
        session.commit()
    finally:
        session.close()


# ── USDA fixture builders ──────────────────────────────────────────

# Reused across multiple states — one fdc id (167512) appears in three
# different consumer interactions.
_FDC_167512_DETAIL = {
    "fdcId": 167512,
    "dataType": "Foundation",
    "description": "Chicken, broilers or fryers",
    "foodCategory": {"id": 5, "code": "0500", "description": "Poultry Products"},
    "foodNutrients": [
        {
            "type": "FoodNutrient",
            "id": 1001,
            "amount": 22.5,
            "nutrient": {"id": 1003, "number": "203", "name": "Protein", "rank": 600, "unitName": "g"},
        },
    ],
}

_SEARCH_CHICKEN = {
    "totalHits": 1,
    "currentPage": 1,
    "totalPages": 1,
    "foods": [
        {
            "fdcId": 167512,
            "description": "Chicken, broilers or fryers",
            "dataType": "Foundation",
            "foodCategory": "Poultry Products",
            "foodNutrients": [
                {
                    "nutrientId": 1003,
                    "nutrientName": "Protein",
                    "nutrientNumber": "203",
                    "unitName": "G",
                    "value": 22.5,
                },
            ],
        },
    ],
}


# ── State handlers ─────────────────────────────────────────────────
# Every distinct provider-state name referenced by a consumer pact must
# appear here. Adding a new consumer state without a handler is a build
# error (we run with enable_pending=False).

def _state_fdc_167512_not_imported():
    """POST /usda/import/167512 — empty import_log, mapping for #203, USDA detail staged."""
    _seed_nutrient_mapping(usda_number=203, usda_name="Protein", nutrient_name="Protein")
    USDA_FOOD_RESPONSES[167512] = _FDC_167512_DETAIL


def _state_fdc_167512_previewable():
    """GET /usda/preview/167512 — mapping for #203 + USDA detail staged."""
    _seed_nutrient_mapping(usda_number=203, usda_name="Protein", nutrient_name="Protein")
    USDA_FOOD_RESPONSES[167512] = _FDC_167512_DETAIL


def _state_search_chicken_has_results():
    """GET /usda/search?q=chicken — stage canned USDA search response."""
    USDA_SEARCH_RESPONSES["chicken"] = _SEARCH_CHICKEN


def _state_at_least_one_mapping():
    """GET /usda/nutrient-map — seed at least one mapping row."""
    _seed_nutrient_mapping(usda_number=203, usda_name="Protein", nutrient_name="Protein")


def _state_mapping_for_203_exists():
    """PUT/DELETE /usda/nutrient-map/203 — row with usda_number=203 exists."""
    _seed_nutrient_mapping(usda_number=203, usda_name="Protein", nutrient_name="Protein")


STATE_HANDLERS = {
    "USDA fdc 167512 has not been imported yet": _state_fdc_167512_not_imported,
    "USDA fdc 167512 has a preview-able nutrient set": _state_fdc_167512_previewable,
    "USDA search returns results for 'chicken'": _state_search_chicken_has_results,
    "at least one USDA nutrient mapping exists": _state_at_least_one_mapping,
    "USDA nutrient mapping for usda_number 203 exists": _state_mapping_for_203_exists,
}


@provider_states.route("/_pact/provider-states", methods=["POST"])
def handle_provider_state():
    data = request.get_json() or {}
    state_name = data.get("state", "")
    action = data.get("action", "setup")

    # Reset between every state so handlers compose from a clean slate.
    _reset()

    if action != "setup":
        return jsonify({"status": "ok"})

    handler = STATE_HANDLERS.get(state_name)
    if handler is None:
        return (
            jsonify({"error": f"Unknown provider state: {state_name!r}"}),
            500,
        )
    handler()
    return jsonify({"status": "ok"})
