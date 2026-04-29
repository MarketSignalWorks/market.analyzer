"""
CRUD endpoints for saved strategies.
"""

from flask import Blueprint, jsonify, request

from backend.models import db, Strategy
from backend.strategies.templates import TEMPLATES

strategies_bp = Blueprint("strategies", __name__, url_prefix="/api/strategies")


@strategies_bp.get("")
def list_strategies():
    rows = Strategy.query.order_by(Strategy.created_at.desc()).all()
    return jsonify([s.to_dict() for s in rows])


@strategies_bp.get("/<int:strategy_id>")
def get_strategy(strategy_id: int):
    s = Strategy.query.get(strategy_id)
    if s is None:
        return jsonify({"error": "Strategy not found"}), 404
    return jsonify(s.to_dict())


@strategies_bp.post("")
def create_strategy():
    payload = request.get_json(force=True, silent=True) or {}
    name = (payload.get("name") or "").strip()
    strategy_type = payload.get("strategy_type")

    if not name:
        return jsonify({"error": "name is required"}), 400
    if strategy_type not in TEMPLATES:
        return jsonify({"error": f"unknown strategy_type: {strategy_type}"}), 400

    s = Strategy(
        name=name,
        description=payload.get("description", ""),
        strategy_type=strategy_type,
        parameters=payload.get("parameters") or {},
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(s.to_dict()), 201


@strategies_bp.put("/<int:strategy_id>")
def update_strategy(strategy_id: int):
    s = Strategy.query.get(strategy_id)
    if s is None:
        return jsonify({"error": "Strategy not found"}), 404

    payload = request.get_json(force=True, silent=True) or {}
    if "name" in payload:
        s.name = payload["name"]
    if "description" in payload:
        s.description = payload["description"]
    if "parameters" in payload:
        s.parameters = payload["parameters"] or {}
    if "strategy_type" in payload:
        if payload["strategy_type"] not in TEMPLATES:
            return jsonify({"error": "unknown strategy_type"}), 400
        s.strategy_type = payload["strategy_type"]

    db.session.commit()
    return jsonify(s.to_dict())


@strategies_bp.delete("/<int:strategy_id>")
def delete_strategy(strategy_id: int):
    s = Strategy.query.get(strategy_id)
    if s is None:
        return jsonify({"error": "Strategy not found"}), 404
    db.session.delete(s)
    db.session.commit()
    return "", 204
