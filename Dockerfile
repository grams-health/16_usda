# ---- Base ----
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Test ----
FROM base AS test
COPY src/ src/
COPY pytest.ini .
CMD ["pytest", "src/", "-v", "--tb=short"]

# ---- Production ----
FROM base AS production
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY --chown=appuser:appgroup src/ src/
COPY --chown=appuser:appgroup docker_entrypoint.py .
COPY --chown=appuser:appgroup gunicorn.conf.py .
USER appuser
EXPOSE 6036
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:6036/health')"
ENTRYPOINT ["python", "docker_entrypoint.py"]
CMD ["gunicorn", "--config", "gunicorn.conf.py", "--bind", "0.0.0.0:6036", "--workers", "2", "--preload", "src.app.app:app"]
