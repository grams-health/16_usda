import os
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


# Initialize shared database
from ..core.database import init_db, Base, get_engine

_DB_URL = os.environ.get("DATABASE_URL", "sqlite:///usda_integration.db")
init_db(_DB_URL)

# Import all model modules to register them on the shared Base
from ..core.own.import_log import db as import_log_db  # noqa: F401
from ..core.own.nutrient_map import db as nutrient_map_db  # noqa: F401

# Import route handlers
from ..rest.nutrient_map.create import handle_create_mapping
from ..rest.nutrient_map.list import handle_list_mappings, handle_get_mapping
from ..rest.nutrient_map.modify import handle_modify_mapping
from ..rest.nutrient_map.remove import handle_remove_mapping
from ..rest.search import handle_search
from ..rest.preview import handle_preview
from ..rest.import_food import handle_import

# Register nutrient-map routes
app.add_url_rule("/usda/nutrient-map", "list_mappings", handle_list_mappings, methods=["GET"])
app.add_url_rule("/usda/nutrient-map", "create_mapping", handle_create_mapping, methods=["POST"])
app.add_url_rule("/usda/nutrient-map/<int:usda_number>", "get_mapping", handle_get_mapping, methods=["GET"])
app.add_url_rule("/usda/nutrient-map/<int:usda_number>", "modify_mapping", handle_modify_mapping, methods=["PUT"])
app.add_url_rule("/usda/nutrient-map/<int:usda_number>", "remove_mapping", handle_remove_mapping, methods=["DELETE"])

# Register function routes
app.add_url_rule("/usda/search", "search", handle_search, methods=["GET"])
app.add_url_rule("/usda/preview/<int:fdc_id>", "preview", handle_preview, methods=["GET"])
app.add_url_rule("/usda/import/<int:fdc_id>", "import_food", handle_import, methods=["POST"])

# Testing-only reset endpoint
if os.environ.get("ENABLE_TESTING_RESET") == "true":
    def _handle_testing_reset():
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                try:
                    conn.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE"))
                except Exception:
                    conn.execute(text(f"DELETE FROM {table.name}"))
            conn.commit()
        # Invalidate cached nutrient map
        from ..core.ref.admin.nutrients import invalidate_cache
        invalidate_cache()
        return jsonify({"status": "ok", "message": "All tables truncated"}), 200

    app.add_url_rule("/testing/reset", "testing_reset", _handle_testing_reset, methods=["POST"])
