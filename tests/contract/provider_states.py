"""Provider-state setup for Pact verification.

Each `given:` clause from a consumer pact maps to a setup function that
puts the provider into the required state (typically by seeding the DB).

We start minimal: any state without a registered handler is a no-op,
which means the verifier reports the interaction as PENDING when the
state is missing — exactly the right "phase 1" outcome. Add specific
handlers as consumer pacts mature.
"""
from flask import Blueprint, jsonify, request

provider_states = Blueprint("provider_states", __name__)

STATE_HANDLERS = {}


def state(name):
    """Register a setup function for a given provider-state name."""
    def decorator(fn):
        STATE_HANDLERS[name] = fn
        return fn
    return decorator


@provider_states.route("/_pact/provider-states", methods=["POST"])
def handle_provider_state():
    data = request.get_json() or {}
    state_name = data.get("state", "")
    action = data.get("action", "setup")
    if action == "setup" and state_name in STATE_HANDLERS:
        STATE_HANDLERS[state_name]()
    return jsonify({"status": "ok"})


# ── State handlers ─────────────────────────────────────────────────
# Add @state("...") handlers here as needed. Unregistered states are
# no-ops; the verifier marks the corresponding pact interactions as
# PENDING.
