"""
STRATEX - Flask Backend Entry Point.

Run from the project root with:
    python -m backend.app
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

import config
from backend.models import db
from backend.routes.backtest import backtest_bp
from backend.routes.meta import meta_bp
from backend.routes.reports import reports_bp
from backend.routes.strategies import strategies_bp


def _resolve_database_uri() -> str:
    """Resolve DATABASE_URI relative to the project root and ensure the dir exists."""
    uri = os.environ.get("DATABASE_URI", config.DATABASE_URI)
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        rel = uri.replace("sqlite:///", "", 1)
        project_root = Path(__file__).resolve().parents[1]
        abs_path = (project_root / rel).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        uri = f"sqlite:///{abs_path.as_posix()}"
    return uri


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    with app.app_context():
        db.create_all()

    app.register_blueprint(meta_bp)
    app.register_blueprint(strategies_bp)
    app.register_blueprint(backtest_bp)
    app.register_blueprint(reports_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=config.API_HOST, port=config.API_PORT, debug=True)
