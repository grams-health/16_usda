"""USDA FoodData Central client with production-grade resilience.

Design contract:
  * Every public method is idempotent (only GETs against USDA).
  * Caller-visible exceptions are typed; callers handle the specific
    failure mode they care about, not status codes.
  * Internal retries are invisible to the caller — they fire on
    transient errors and the caller only sees the final outcome.
  * Every call emits structured telemetry (latency, served-by IP,
    outcome) so operators can confirm "USDA edge X is bad" from a
    dashboard, not by grepping logs.

Failure-mode taxonomy:
  * UsdaConfigError      → API key missing / bad config (fail fast)
  * UsdaRateLimitError   → 429 from USDA (caller backs off)
  * UsdaFoodNotFoundError → JSON 404 for a real fdc_id (terminal)
  * UsdaTransientError   → transport/content-shape (retried internally)
  * UsdaApiError         → catch-all base + non-transient API failures

Layered defense (cheap → expensive):
  1. urllib3.Retry on the HTTPAdapter — handles transport-level
     transient failure (DNS, connect, 5xx, 429 with Retry-After).
  2. Response-shape validation — JSON 404 is terminal (real
     not-found), HTML 404 is transient (misrouted-edge symptom);
     transient → tenacity retries with backoff.
  3. Per-IP health tracking + pool drain on quarantine — three
     consecutive transient failures from one resolved IP force a
     session close so the next attempt re-resolves DNS and (statistically)
     lands on a different edge.
  4. Structured `/health` snapshot — operators see "edge 15.200.48.244
     has 47 consecutive failures, quarantined since 14:22 UTC" without
     grepping logs.

The root failure mode this defends against is concrete and reproducible:
api.nal.usda.gov is DNS-round-robin'd across multiple edges, and at
least one of them (observed: 15.200.48.244) serves the FoodData Central
marketing landing page with HTTP 404 + text/html for /fdc/v1/* paths
instead of routing to the API backend. Layered defense survives this
without an outage; observability surfaces the bad edge so we can file
a USDA ticket with hard data.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)
from urllib3.util.retry import Retry

from ..typing.usda import UsdaFoodDetail, UsdaNutrient, UsdaSearchResult


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception taxonomy
# ---------------------------------------------------------------------------


class UsdaApiError(Exception):
    """Base for USDA-client failures. Never raised directly — callers
    handle one of the subclasses."""


class UsdaConfigError(UsdaApiError):
    """USDA_API_KEY missing or invalid. Fail-fast at startup, not on
    first request — a misconfigured deploy should refuse to boot, not
    silently 500 the first user that searches for chicken."""


class UsdaRateLimitError(UsdaApiError):
    """USDA returned 429. Caller should back off or surface to user.
    Not retried internally — rate-limit retries belong to the caller."""


class UsdaFoodNotFoundError(UsdaApiError):
    """USDA returned a proper JSON 404 for an unknown fdc_id. Terminal,
    not transient: the resource genuinely doesn't exist."""


class UsdaTransientError(UsdaApiError):
    """Transport failure, unexpected content type, or 5xx. Internally
    retried via tenacity; only raised to the caller after every retry
    attempt fails. Carries the last-seen remote IP so operators can
    correlate with the per-IP health snapshot."""

    def __init__(self, message: str, *, remote_ip: str | None = None) -> None:
        super().__init__(message)
        self.remote_ip = remote_ip


# ---------------------------------------------------------------------------
# Per-IP health tracking
# ---------------------------------------------------------------------------


@dataclass
class _IpHealth:
    """In-memory failure/success counters per resolved upstream IP.

    Process-local. When this process restarts, counters reset. Good
    enough for operator visibility; if you need cross-instance state,
    push to Redis or delegate to a service mesh — that's mesh territory
    and not built here."""

    successes: int = 0
    failures: int = 0
    last_failure_ts: float = 0.0
    consecutive_failures: int = 0

    def record_success(self) -> None:
        self.successes += 1
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.failures += 1
        self.consecutive_failures += 1
        self.last_failure_ts = time.time()

    @property
    def is_quarantined(self) -> bool:
        """Three consecutive transient failures within 5 minutes is the
        quarantine threshold. On quarantine, the client drains the
        connection pool so the next request re-resolves DNS and likely
        picks a different A record."""
        return (
            self.consecutive_failures >= 3
            and (time.time() - self.last_failure_ts) < 300
        )


_ip_health: dict[str, _IpHealth] = {}


def ip_health_snapshot() -> dict[str, dict[str, Any]]:
    """Per-IP health, suitable for exposing via /health/usda. Operators
    use this to confirm which USDA edge is misbehaving without grepping
    logs."""
    return {
        ip: {
            "successes": h.successes,
            "failures": h.failures,
            "consecutive_failures": h.consecutive_failures,
            "quarantined": h.is_quarantined,
            "last_failure_age_s": (
                int(time.time() - h.last_failure_ts)
                if h.last_failure_ts > 0
                else None
            ),
        }
        for ip, h in _ip_health.items()
    }


def reset_ip_health() -> None:
    """Clear all per-IP health state. Intended for tests; do not call
    in production."""
    _ip_health.clear()


# ---------------------------------------------------------------------------
# Session construction
# ---------------------------------------------------------------------------


USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Identifies our service to USDA so if our calls become problematic they
# can contact us. Generic python-requests/X.Y.Z is anonymous and useless
# for incident correlation.
_USER_AGENT = (
    "grams-usda-client/1.0 "
    "(+https://gramshealth.com; usda-client@gramshealth.com)"
)

# (connect_seconds, read_seconds). Connect should be aggressive so we
# fail fast on a dead edge; read can be patient because USDA's API is
# legitimately slow on cold paths.
_TIMEOUT: tuple[float, float] = (3.0, 10.0)


def _build_session() -> requests.Session:
    """Single shared session with a mounted HTTPAdapter carrying the
    transport-layer Retry policy. urllib3.Retry handles DNS / connect /
    5xx / 429 automatically; we own everything above (content shape,
    typed exceptions, IP tracking)."""
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
    })
    adapter = HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            # Idempotent methods only — even if a POST helper is added
            # later, urllib3 won't auto-retry it.
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
            respect_retry_after_header=True,
            # We own status → exception mapping; let raise_on_status
            # stay False so transport returns the response object.
            raise_on_status=False,
        ),
        pool_connections=10,
        pool_maxsize=10,
    )
    session.mount("https://", adapter)
    return session


_session: requests.Session = _build_session()


def _drain_pool() -> None:
    """Close all pooled connections so the next request re-resolves
    DNS. Triggered when an upstream IP is quarantined — the next
    request statistically lands on a different A record."""
    global _session
    _session.close()
    _session = _build_session()


# ---------------------------------------------------------------------------
# Config (fail-fast)
# ---------------------------------------------------------------------------


def _get_api_key() -> str:
    """Resolve the API key from env or fail with UsdaConfigError. The
    raise propagates immediately — no retry, no swallowing."""
    key = os.environ.get("USDA_API_KEY", "").strip()
    if not key:
        raise UsdaConfigError("USDA_API_KEY environment variable not set")
    return key


# ---------------------------------------------------------------------------
# Core request helper
# ---------------------------------------------------------------------------


def _remote_ip_from_response(resp: requests.Response) -> str | None:
    """Extract the IP that actually served this response. urllib3
    keeps it on the underlying connection but doesn't expose it on
    Response; we reach through `resp.raw._connection.sock.getpeername()`
    (urllib3 issue #1071). Best-effort: returns None if introspection
    fails — IP tracking degrades to "unknown" bucket rather than
    crashing."""
    try:
        return resp.raw._connection.sock.getpeername()[0]  # type: ignore[union-attr]
    except Exception:
        return None


def _is_json_content(resp: requests.Response) -> bool:
    return (
        resp.headers.get("content-type", "")
        .lower()
        .startswith("application/json")
    )


def _record_outcome(
    served_by: str | None, *, success: bool,
) -> tuple[_IpHealth, bool]:
    """Update per-IP counters; return (health entry, just-quarantined).
    `just_quarantined` is True iff this failure transitioned the IP
    from healthy to quarantined — used to log the event once instead
    of on every subsequent failure."""
    key = served_by or "unknown"
    health = _ip_health.setdefault(key, _IpHealth())
    was_quarantined = health.is_quarantined
    if success:
        health.record_success()
    else:
        health.record_failure()
    just_quarantined = health.is_quarantined and not was_quarantined
    return health, just_quarantined


@retry(
    retry=retry_if_exception_type(UsdaTransientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.5, max=5.0),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def _get_json(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """Issue a GET against USDA FDC, validate response shape, return
    parsed JSON. Retries up to 3 times on UsdaTransientError only;
    everything else propagates immediately so callers see real errors
    fast."""
    url = f"{USDA_BASE_URL}{path}"
    full_params = {**params, "api_key": _get_api_key()}

    started = time.monotonic()
    try:
        resp = _session.get(url, params=full_params, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        # Connect / read / SSL — transient at the transport layer.
        log.warning(
            "usda.transport_error path=%s err=%s",
            path, f"{type(exc).__name__}: {exc}",
        )
        raise UsdaTransientError(
            f"transport: {type(exc).__name__}: {exc}"
        ) from exc

    elapsed_ms = int((time.monotonic() - started) * 1000)
    served_by = _remote_ip_from_response(resp)

    # Structured outcome log — every call, success or failure. Operators
    # filter on `usda.call` to see the request volume per edge.
    log.info(
        "usda.call path=%s status=%d ct=%r bytes=%d elapsed_ms=%d served_by=%s",
        path,
        resp.status_code,
        resp.headers.get("content-type", ""),
        len(resp.content),
        elapsed_ms,
        served_by,
    )

    # 429 → typed exception, no internal retry (caller decides).
    if resp.status_code == 429:
        _, just_q = _record_outcome(served_by, success=False)
        if just_q:
            log.warning("usda.ip_quarantined ip=%s reason=429", served_by)
            _drain_pool()
        raise UsdaRateLimitError("USDA API rate limit exceeded")

    # Status-aware content validation. We MUST distinguish "real 404
    # from USDA's API" (JSON, terminal) from "misrouted-edge 404 with
    # marketing HTML" (HTML, transient).
    if not _is_json_content(resp):
        _, just_q = _record_outcome(served_by, success=False)
        if just_q:
            log.warning(
                "usda.ip_quarantined ip=%s reason=non_json_content "
                "draining_pool=true",
                served_by,
            )
            _drain_pool()
        raise UsdaTransientError(
            f"non-JSON response from {served_by} "
            f"(status={resp.status_code}, "
            f"content-type={resp.headers.get('content-type', '')!r}); "
            f"body[:200]={resp.text[:200]!r}",
            remote_ip=served_by,
        )

    if resp.status_code == 404:
        # Proper JSON 404 — terminal. USDA confirmed the resource
        # doesn't exist; retrying won't help. The edge that served
        # this is healthy.
        _record_outcome(served_by, success=True)
        raise UsdaFoodNotFoundError(
            f"USDA resource not found: {path}"
        )

    if resp.status_code >= 500:
        # urllib3.Retry already retried these; if we got here, all
        # transport retries were exhausted. Treat as transient at the
        # tenacity layer so we attempt one more round with a fresh
        # connection.
        _, just_q = _record_outcome(served_by, success=False)
        if just_q:
            log.warning(
                "usda.ip_quarantined ip=%s reason=%d", served_by, resp.status_code,
            )
            _drain_pool()
        raise UsdaTransientError(
            f"USDA {resp.status_code}: {resp.text[:200]}",
            remote_ip=served_by,
        )

    if resp.status_code >= 400:
        # Non-404 4xx (400 bad request, 401, 403, etc.) — not
        # transient; the request itself is wrong.
        _record_outcome(served_by, success=False)
        raise UsdaApiError(
            f"USDA {resp.status_code}: {resp.text[:200]}"
        )

    # 2xx + JSON: success path.
    _record_outcome(served_by, success=True)
    try:
        return resp.json()
    except ValueError as exc:
        # Content-Type said JSON but body wasn't parseable. Truly
        # transient — surface as such.
        _record_outcome(served_by, success=False)
        raise UsdaTransientError(
            f"malformed JSON from {served_by}: {exc}; "
            f"body[:200]={resp.text[:200]!r}",
            remote_ip=served_by,
        ) from exc


# ---------------------------------------------------------------------------
# Parsers — convert USDA response shape → core types
# ---------------------------------------------------------------------------


def _parse_search_result(food: dict[str, Any]) -> UsdaSearchResult:
    nutrients: list[UsdaNutrient] = []
    for fn in food.get("foodNutrients", []):
        try:
            num = int(float(fn["nutrientNumber"]))
        except (ValueError, TypeError, KeyError):
            continue
        nutrients.append(UsdaNutrient(
            number=num,
            name=fn.get("nutrientName", ""),
            value=float(fn.get("value", 0)),
            unit=fn.get("unitName", ""),
        ))
    return UsdaSearchResult(
        fdc_id=food["fdcId"],
        description=food["description"],
        food_category=food.get("foodCategory", ""),
        nutrients=nutrients,
        data_type=food.get("dataType", ""),
    )


def _parse_food_detail(data: dict[str, Any]) -> UsdaFoodDetail:
    food_category = ""
    fc = data.get("foodCategory")
    if isinstance(fc, dict):
        food_category = fc.get("description", "")
    elif isinstance(fc, str):
        food_category = fc

    nutrients: list[UsdaNutrient] = []
    for fn in data.get("foodNutrients", []):
        nutrient = fn.get("nutrient", {})
        try:
            num = int(float(nutrient["number"]))
        except (ValueError, TypeError, KeyError):
            continue
        nutrients.append(UsdaNutrient(
            number=num,
            name=nutrient.get("name", ""),
            value=float(fn.get("amount", 0)),
            unit=nutrient.get("unitName", ""),
        ))

    return UsdaFoodDetail(
        fdc_id=data["fdcId"],
        description=data["description"],
        food_category=food_category,
        nutrients=nutrients,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_foods(
    query: str, page_size: int = 25,
) -> list[UsdaSearchResult]:
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")
    data = _get_json("/foods/search", {
        "query": query,
        "dataType": "Foundation,SR Legacy",
        "pageSize": page_size,
    })
    results = [_parse_search_result(f) for f in data.get("foods", [])]
    # Sort by nutrient count descending — most complete entries first.
    results.sort(key=lambda r: len(r.nutrients), reverse=True)
    return results


def get_food(fdc_id: int) -> UsdaFoodDetail:
    data = _get_json(f"/food/{fdc_id}", {})
    return _parse_food_detail(data)
