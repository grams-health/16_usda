"""Gunicorn configuration for USDA import service.

Disposes SQLAlchemy engine connection pools after fork so each worker
gets its own fresh connections instead of sharing the master's sockets.
"""


def post_fork(server, worker):
    from src.core.own.import_log.db import _engine as import_log_engine
    from src.core.own.nutrient_map.db import _engine as nutrient_map_engine

    if import_log_engine is not None:
        import_log_engine.dispose(close=False)

    if nutrient_map_engine is not None:
        nutrient_map_engine.dispose(close=False)
