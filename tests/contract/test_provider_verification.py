"""Pact provider verification: 16_usda honours every consumer contract
registered against it in the local broker.

Strict mode: `enable_pending=False`. Every `given:` clause referenced
by a consumer pact must have a corresponding handler registered in
`provider_states.py`. Unmapped states return 500 from the setup
endpoint and the verifier fails — PENDING is no longer tolerated.

This test runs LOCALLY ONLY — there is no CI integration. Run via the
contract Dockerfile stage:
    docker build --target contract -t 16_usda-contract .
    docker run --rm --network host \
        -e PACT_BROKER_URL=http://localhost:9292 \
        16_usda-contract
"""
import os
import threading
import time

import pytest
import requests
from pact import Verifier

PROVIDER_PORT = 5050
PROVIDER_URL = f"http://localhost:{PROVIDER_PORT}"
BROKER_URL = os.environ.get("PACT_BROKER_URL", "http://localhost:9292")


@pytest.fixture(scope="session")
def provider_app():
    """Boot the Flask app in-process with provider-state setup endpoint."""
    from src.app.app import app
    from tests.contract.provider_states import provider_states

    app.register_blueprint(provider_states)

    server = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=PROVIDER_PORT, use_reloader=False),
        daemon=True,
    )
    server.start()

    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            r = requests.get(f"{PROVIDER_URL}/health", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.2)
    else:
        raise RuntimeError(f"provider did not start on {PROVIDER_URL} within 10s")

    yield PROVIDER_URL


def _broker_reachable():
    try:
        return requests.get(BROKER_URL, timeout=3).status_code < 500
    except Exception:
        return False


@pytest.mark.skipif(not _broker_reachable(), reason=f"Pact broker not reachable at {BROKER_URL}")
def test_usda_provider_honors_contracts(provider_app):
    """Verify 16_usda satisfies every consumer contract from the broker."""
    verifier = Verifier(provider="16_usda", provider_base_url=provider_app)

    output, logs = verifier.verify_with_broker(
        broker_url=BROKER_URL,
        provider_states_setup_url=f"{provider_app}/_pact/provider-states",
        enable_pending=False,
        publish_version="local",
        publish_verification_results=False,
        consumer_version_selectors=[{"latest": True}],
    )

    assert output == 0, f"Provider verification failed:\n{logs}"
