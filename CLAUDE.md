# USDA Import Service

## Architecture

3-layer architecture: core → service → rest. Port 6036.

```
src/
├── app/app.py              Flask app with route registration + /health + DB init
├── core/
│   ├── typing/             Core type classes (primitives, entities, Status)
│   │   ├── primitives.py   FdcId, UsdaNumber, UsdaName, NutrientName
│   │   ├── status.py       Status with __bool__
│   │   ├── import_log.py   ImportLog class
│   │   ├── nutrient_map.py NutrientMapping class
│   │   ├── usda.py         UsdaSearchResult, UsdaFoodDetail, UsdaNutrient
│   │   └── transform.py    TransformedFood, TransformedNutrient
│   ├── own/
│   │   ├── import_log/     Import tracking (create, list) — no REST exposure
│   │   │   ├── db.py
│   │   │   ├── create.py
│   │   │   ├── list.py
│   │   │   └── test/
│   │   └── nutrient_map/   USDA→admin nutrient mapping CRUD
│   │       ├── db.py
│   │       ├── create.py
│   │       ├── list.py
│   │       ├── modify.py
│   │       ├── remove.py
│   │       └── test/
│   ├── ref/
│   │   └── admin/          Admin service client
│   │       ├── nutrients.py    GET /nutrients + resolution logic
│   │       └── create_food.py  POST /foods/with-nutrients
│   ├── usda/
│   │   └── client.py       USDA FoodData Central API client
│   ├── search.py           Search orchestration
│   ├── preview.py          Preview orchestration
│   ├── import_food.py      Import orchestration
│   ├── transform.py        USDA → admin data transformation
│   └── test/               Tests for client, transform, search, preview, import
├── service/                Type conversion layer (core types ↔ REST types)
│   ├── nutrient_map/
│   ├── search.py
│   ├── preview.py
│   └── import_food.py
└── rest/                   Flask request/response handlers
    ├── typing/             REST dataclasses (primitives, entities, Status)
    ├── nutrient_map/       CRUD handlers for /usda/nutrient-map
    ├── search.py           GET /usda/search
    ├── preview.py          GET /usda/preview/<fdc_id>
    ├── import_food.py      POST /usda/import/<fdc_id>
    └── test/
```

## Conventions

### Types

**Core types** (`src/core/typing/`):
- Plain classes with `__init__`, NOT dataclasses
- Custom primitive types inheriting from `int`, `str`, or `float` with validation
- Status class with `__bool__` returning `status == "success"`

**REST types** (`src/rest/typing/`):
- `@dataclass` classes for serialization via `asdict()`
- Simple type aliases (not custom classes) for primitives

### Layers

- **Core**: Business logic. Uses core types. Owns DB sessions (try/finally with close).
- **Service**: Type conversion only. Converts REST primitives → core types, calls core, converts results back.
- **Rest**: Flask request/response handling. Parses JSON/query params, calls service, returns jsonify.

### Database

- Two tables: `import_log` and `nutrient_map`, each with independent `Base`, `_engine`, `_Session`, `init_db()`, `get_session()`
- Sessions always closed in `finally` blocks
- `IntegrityError` caught and returns error Status with rollback

### USDA-Specific

- All USDA API calls go through `src/core/usda/client.py` using the `requests` library
- USDA API key loaded from `USDA_API_KEY` env var
- Rate limit errors (HTTP 429) raise `UsdaRateLimitError`, returned as 429 to client
- Nutrient mapping stored in DB (`nutrient_map` table), not hardcoded
- Nutrient resolution: read mapping from DB → fetch admin nutrients → match by name → cache
- Cache invalidated when nutrient_map is modified via CRUD endpoints
- Admin service calls use `requests` library, base URL from `ADMIN_SERVICE_URL` env var
- All USDA quantities converted from per-100g to per-gram (divide by 100)
- Carbohydrates computed as USDA #205 minus USDA #291 (fiber excluded)
- Paired amino acids (Met #506, Cys #507, Phe #508, Tyr #509) stored individually

### Error Handling

- 400: Missing or invalid fields (empty search query, missing mapping fields)
- 404: USDA food not found, nutrient mapping not found
- 409: Already imported (fdc_id in import_log), duplicate mapping (usda_number exists)
- 429: USDA API rate limited (pass through)

### Testing

- All tests run in Docker: `docker build --target test -t usda-test . && docker run --rm usda-test`
- Core tests in `src/core/own/<entity>/test/` and `src/core/test/`
- REST tests in `src/rest/test/`
- Mock USDA API calls using `unittest.mock.patch` on `requests.get`
- Mock admin service calls using `unittest.mock.patch` on `requests.get`/`requests.post`
- JSON fixtures in `src/core/test/fixtures/` captured from real USDA API responses
- In-memory SQLite for import_log and nutrient_map tests

## Commands

- `python -m pytest src/ -v` — run all tests
