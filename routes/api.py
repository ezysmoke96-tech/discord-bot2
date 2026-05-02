from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.route("/hello")
def hello():
    return jsonify({"message": "Hello from the Python API!"})
