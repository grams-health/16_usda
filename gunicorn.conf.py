"""Gunicorn configuration for USDA import service.

Disposes SQLAlchemy engine connection pools after fork so each worker
gets its own fresh connections instead of sharing the master's sockets.
"""


def post_fork(server, worker):
    from src.core.database import _engine

    if _engine is not None:
        _engine.dispose(close=False)
