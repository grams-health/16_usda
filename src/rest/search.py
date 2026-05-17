from flask import jsonify, request

from ..core.usda.client import (
    UsdaApiError,
    UsdaConfigError,
    UsdaRateLimitError,
    UsdaTransientError,
)
from ..service.search import search_usda_foods


def handle_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing or empty q parameter"}), 400

    try:
        results = search_usda_foods(query)
        return jsonify({"results": results}), 200
    except UsdaRateLimitError:
        return jsonify({"status": "error", "message": "USDA API rate limit exceeded"}), 429
    except UsdaConfigError as exc:
        # Misconfigured deploy — surface a clear 503 so ops sees the
        # real cause instead of an opaque 500.
        return jsonify({
            "status": "error",
            "message": "USDA client misconfigured",
            "detail": str(exc),
        }), 503
    except UsdaTransientError as exc:
        # All retries exhausted. The upstream is unreachable or its
        # edge is misrouted. 502 Bad Gateway is the RFC-correct
        # status; include the served-by IP if available so operators
        # can correlate with /health/usda.
        body = {"status": "error", "message": "USDA upstream temporarily unavailable"}
        if exc.remote_ip:
            body["upstream_ip"] = exc.remote_ip
        return jsonify(body), 502
    except UsdaApiError as exc:
        # Catch-all for non-transient USDA failures (400, 401, 403, etc.).
        # These are not retried — the request itself was wrong.
        return jsonify({"status": "error", "message": str(exc)}), 502
