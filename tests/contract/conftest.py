"""Shared fixtures for Pact provider verification.

Boots a fresh SQLite file and creates the import_log + nutrient_map
schemas before any contract test imports `src.app.app` (which calls
`init_db` with `DATABASE_URL`). Both this conftest and the app must
point at the *same* DB URL so the provider sees the rows that the
state handlers seed.

A file-backed SQLite is used (rather than `sqlite:///:memory:`) because
each `create_engine("sqlite:///:memory:")` call returns a *distinct*
in-memory database, so the conftest and app.py would diverge.

Also installs module-level fakes for `requests.get` / `requests.post`
so the running provider never hits the real USDA FoodData Central API
or the live admin service. State handlers stage the canned responses
they need by mutating the dicts exposed below.
"""
import os
import tempfile

# Use a fresh per-run SQLite file. Set this BEFORE importing src.app.app
# anywhere in the test session.
_DB_PATH = os.path.join(tempfile.gettempdir(), "usda_pact.db")
if os.path.exists(_DB_PATH):
    os.remove(_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ.setdefault("USDA_API_KEY", "pact-test-key")
os.environ.setdefault("ADMIN_SERVICE_URL", "http://admin-mock.local")

from src.core.database import init_db, Base, get_engine  # noqa: E402
from src.core.own.import_log import db as _import_log_db  # noqa: F401,E402
from src.core.own.nutrient_map import db as _nutrient_map_db  # noqa: F401,E402

init_db(os.environ["DATABASE_URL"])
Base.metadata.create_all(get_engine())


# ── HTTP fakes ─────────────────────────────────────────────────────
# 16_usda's REST handlers call out to the USDA FoodData Central API
# and to the admin service via `requests`. We replace the module-level
# `requests.get` / `requests.post` with dispatching fakes that pull
# canned bodies out of the dicts below — state handlers populate them
# before each interaction is verified.
import requests as _requests  # noqa: E402

_orig_get = _requests.get
_orig_post = _requests.post


# Mutable registries the provider-state handlers stage values into.
USDA_SEARCH_RESPONSES: dict = {}   # query (lowercase) -> raw USDA JSON
USDA_FOOD_RESPONSES: dict = {}     # fdc_id -> raw USDA JSON
ADMIN_NUTRIENTS_RESPONSE: list = []
ADMIN_CREATE_FOOD_RESPONSE: dict = {
    "status": "success",
    "message": "imported",
    "data": {"food_id": 1},
}


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        import json as _json_mod
        self._json = json_data
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.content = _json_mod.dumps(json_data).encode("utf-8")
        self.text = self.content.decode("utf-8")
        self.raw = type("FakeRaw", (), {"_connection": None})()

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise _requests.HTTPError(f"HTTP {self.status_code}")


def _fake_get(url, params=None, **kwargs):
    # USDA search
    if "api.nal.usda.gov" in url and "/foods/search" in url:
        query = (params or {}).get("query", "").strip().lower()
        body = USDA_SEARCH_RESPONSES.get(query, {"foods": []})
        return _FakeResponse(body)
    # USDA food detail
    if "api.nal.usda.gov" in url and "/food/" in url:
        try:
            fdc_id = int(url.rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            return _FakeResponse({"error": "bad fdc"}, status_code=400)
        body = USDA_FOOD_RESPONSES.get(fdc_id)
        if body is None:
            return _FakeResponse({"error": "not found"}, status_code=404)
        return _FakeResponse(body)
    # Admin /nutrients
    if "/nutrients" in url and "admin-mock" in url:
        return _FakeResponse(ADMIN_NUTRIENTS_RESPONSE)
    return _orig_get(url, params=params, **kwargs)


def _fake_post(url, json=None, **kwargs):
    # Only intercept the admin service URL — leave pact-mock-service
    # traffic (used by the consumer tests) untouched.
    if "admin-mock" in url and "/foods/with-nutrients" in url:
        return _FakeResponse(ADMIN_CREATE_FOOD_RESPONSE, status_code=201)
    return _orig_post(url, json=json, **kwargs)


_requests.get = _fake_get
_requests.post = _fake_post

# The production USDA client uses requests.Session().get(...), which
# bypasses the module-level requests.get patch above. Patch Session
# methods as well so provider verification doesn't try to reach the
# real USDA API or admin service.
_orig_session_get = _requests.Session.get
_orig_session_post = _requests.Session.post


def _fake_session_get(self, url, params=None, **kwargs):
    return _fake_get(url, params=params, **kwargs)


def _fake_session_post(self, url, json=None, **kwargs):
    return _fake_post(url, json=json, **kwargs)


_requests.Session.get = _fake_session_get
_requests.Session.post = _fake_session_post
