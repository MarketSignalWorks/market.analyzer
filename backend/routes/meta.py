"""
Static metadata endpoints: strategy templates and the symbol universe.
"""

from flask import Blueprint, jsonify

from backend.strategies.templates import TEMPLATES, SYMBOLS

meta_bp = Blueprint("meta", __name__, url_prefix="/api")


@meta_bp.get("/templates")
def list_templates():
    return jsonify(TEMPLATES)


@meta_bp.get("/symbols")
def list_symbols():
    return jsonify(SYMBOLS)
