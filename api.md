# USDA Import Service REST API

Base URL: `http://localhost:6036`

## Entities

### Owned
- `import_log` — Tracks which USDA foods have been imported and their corresponding admin food IDs
- `nutrient_map` — Configurable mapping from USDA nutrient numbers to admin nutrient names

### Reference
- `admin` — calls `GET /nutrients` for nutrient name resolution, `POST /foods/with-nutrients` to create imported foods

### Functions
- `search` — Search USDA FoodData Central Foundation Foods, annotate with imported status
- `preview` — Fetch a USDA food's nutrient data and map it to admin nutrients with coverage info
- `import_food` — Orchestrate full import: fetch from USDA, transform, create in admin, record in import_log
- `transform` — Map USDA food detail to admin food + food_nutrient payloads (internal, no endpoint)

## Response Conventions

### Status Object

Returned by mutating operations.

```json
{
  "status": "success" | "error",
  "message": "Human-readable message"
}
```

### Status Codes

| Code | Meaning |
|------|---------|
| 200  | Success |
| 201  | Created |
| 400  | Bad request (missing or invalid fields) |
| 404  | Not found (USDA food not found) |
| 409  | Conflict (already imported, duplicate mapping) |
| 429  | Rate limited (USDA API rate limit exceeded) |

---

## ImportLog

Tracks which USDA foods have been imported into admin.

| Field | Type | Description |
|-------|------|-------------|
| `fdc_id` | int | USDA FoodData Central ID (primary key) |
| `food_id` | int | Admin food_id that was created |
| `food_name` | str | Food name at import time |
| `imported_at` | datetime | Auto-generated timestamp |

No REST endpoints. Internal use only by search (imported flags) and import_food (duplicate check, recording).

---

## NutrientMap

Configurable mapping from USDA nutrient numbers to admin nutrient names. Managed through the admin frontend.

| Field | Type | Description |
|-------|------|-------------|
| `usda_number` | int | USDA nutrient number (primary key), e.g., 203 |
| `usda_name` | str | USDA display name, e.g., "Total lipid (fat)" |
| `nutrient_name` | str | Admin nutrient name to match, e.g., "Fat" |

**Routes:**

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/usda/nutrient-map` | List all mappings |
| POST | `/usda/nutrient-map` | Create a mapping |
| GET | `/usda/nutrient-map/<usda_number>` | Get a single mapping |
| PUT | `/usda/nutrient-map/<usda_number>` | Modify a mapping's nutrient_name |
| DELETE | `/usda/nutrient-map/<usda_number>` | Remove a mapping |

**Request fields:**

- `POST /usda/nutrient-map` — `{ "usda_number": 203, "usda_name": "Protein", "nutrient_name": "Protein" }`
- `PUT /usda/nutrient-map/<usda_number>` — `{ "nutrient_name": "Total Protein" }`

**Response shapes:**

`GET /usda/nutrient-map` — `200`
```json
[
  { "usda_number": 203, "usda_name": "Protein", "nutrient_name": "Protein" },
  { "usda_number": 204, "usda_name": "Total lipid (fat)", "nutrient_name": "Fat" }
]
```

`GET /usda/nutrient-map/<usda_number>` — `200` NutrientMap object | `404` if not found

**Status codes:**

| Operation | Codes |
|-----------|-------|
| POST | `201` Status | `400` if missing field | `409` if duplicate usda_number |
| GET (list) | `200` |
| GET (single) | `200` NutrientMap | `404` if not found |
| PUT | `200` Status | `404` if not found | `400` if missing field |
| DELETE | `200` Status | `404` if not found |

---

## Search

Search USDA FoodData Central Foundation Foods by keyword. Results are annotated with an `imported` flag indicating whether the food has already been imported.

### `GET /usda/search`

**Query parameters:**

- `q` (required) — Search keyword, e.g., "chicken"

**Response:** `200`

```json
{
  "results": [
    {
      "fdc_id": 171077,
      "description": "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw",
      "food_category": "Poultry Products",
      "imported": false
    },
    {
      "fdc_id": 171078,
      "description": "Chicken, broilers or fryers, thigh, meat only, raw",
      "food_category": "Poultry Products",
      "imported": true
    }
  ]
}
```

Calls USDA FoodData Central `GET /fdc/v1/foods/search` with `dataType=Foundation`. Checks import_log to set `imported` flags.

**Errors:** `400` missing or empty `q` parameter | `429` USDA API rate limited

---

## Preview

Fetch a single USDA food's full nutrient data and map it to admin nutrients. Shows which nutrients are available and which are missing.

### `GET /usda/preview/<fdc_id>`

**Response:** `200`

```json
{
  "fdc_id": 171077,
  "food_name": "Chicken, broilers or fryers, breast, skinless, boneless, meat only, raw",
  "food_category": "Poultry Products",
  "nutrients": [
    { "nutrient_name": "Protein", "quantity": 0.2250, "unit": "g", "usda_number": 203, "available": true },
    { "nutrient_name": "Fat", "quantity": 0.0262, "unit": "g", "usda_number": 204, "available": true },
    { "nutrient_name": "Carbohydrates", "quantity": 0.0000, "unit": "g", "usda_number": 205, "available": true, "note": "computed: #205 - #291" },
    { "nutrient_name": "Vitamin D", "quantity": null, "unit": "ug", "usda_number": 328, "available": false }
  ],
  "coverage": {
    "available": 28,
    "total": 32,
    "missing": ["Vitamin D", "Starch", "Trans Fat", "Omega-3 (ALA)"]
  }
}
```

Calls USDA FoodData Central `GET /fdc/v1/food/{fdcId}`. Reads nutrient_map from DB, fetches admin nutrients for name→ID resolution, and maps USDA data to admin nutrient names. Quantities converted from per-100g to per-gram. Carbohydrates computed as USDA #205 minus #291.

**Errors:** `404` USDA food not found | `429` USDA API rate limited

---

## Import

Import a USDA food into the admin service. Fetches full nutrient data from USDA, transforms it, and creates the food + food_nutrients in admin via `POST /foods/with-nutrients`. Records the import in import_log.

### `POST /usda/import/<fdc_id>`

**Request:** None (fdc_id in URL path)

**Response:** `201`

```json
{
  "status": "success",
  "message": "Food imported with 28 nutrients",
  "data": { "food_id": 47 }
}
```

**Side effects:**
1. Checks import_log — if fdc_id already imported, returns 409
2. Fetches USDA food detail via API
3. Resolves nutrient mapping (nutrient_map DB → admin GET /nutrients)
4. Transforms USDA data to admin payload (per-gram quantities, computed carbs)
5. Calls admin `POST /foods/with-nutrients` with food_name + nutrients
6. Records fdc_id, food_id, food_name in import_log

**Errors:** `409` already imported | `404` USDA food not found | `429` USDA API rate limited

---

## Transform (Internal)

Not an endpoint. Pure function used by preview and import.

```python
transform_food(detail: UsdaFoodDetail, nutrient_map: dict[int, int]) -> TransformedFood
```

**Rules:**
- All quantities divided by 100 (USDA reports per 100g, admin stores per gram)
- Carbohydrates = USDA #205 value minus USDA #291 value (fiber excluded)
- If #291 absent, carbohydrates = #205 as-is
- Methionine (#506), Cystine (#507), Phenylalanine (#508), Tyrosine (#509) each stored individually
- Nutrients with 0.0 value are included (e.g., trans fat = 0 for chicken)
- Nutrients absent in USDA response are omitted (not zeroed)

---

## Dependencies

### Outgoing
- **Admin service** (`http://admin:6020`):
  - `GET /nutrients` — fetch all nutrients for name→ID resolution
  - `POST /foods/with-nutrients` — create food + food_nutrient rows atomically
- **USDA FoodData Central** (`https://api.nal.usda.gov/fdc/v1`):
  - `GET /foods/search?query=...&dataType=Foundation` — search Foundation Foods
  - `GET /food/{fdcId}` — fetch full nutrient detail for a single food

### Called By
- **Admin frontend** — all USDA endpoints (via admin gateway)

### Environment Variables
- `DATABASE_URL` — PostgreSQL connection string for import_log and nutrient_map tables
- `USDA_API_KEY` — USDA FoodData Central API key (1,000 requests/hour)
- `ADMIN_SERVICE_URL` — admin service base URL (default: `http://localhost:6020`)
