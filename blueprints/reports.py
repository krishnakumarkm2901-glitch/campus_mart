"""
Reports Blueprint – students can report listings.
"""
from flask import Blueprint, request, jsonify, session
from bson import ObjectId
from utils.db import get_db
from utils.decorators import api_login_required
from datetime import datetime

reports_bp = Blueprint("reports", __name__)

VALID_REASONS = [
    "Fake Product",
    "Wrong Category",
    "Spam",
    "Duplicate Listing",
    "Inappropriate Content",
    "Other",
]


@reports_bp.route("/api/reports", methods=["POST"])
@api_login_required
def report_product():
    """Submit a report for a product."""
    db = get_db()
    data = request.get_json()

    product_id = data.get("product_id")
    reason = data.get("reason")
    details = data.get("details", "")

    if not product_id or not reason:
        return jsonify({"error": "product_id and reason are required"}), 400

    if reason not in VALID_REASONS:
        return jsonify({"error": f"Invalid reason. Valid: {VALID_REASONS}"}), 400

    try:
        product = db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        return jsonify({"error": "Invalid product ID"}), 400

    if not product:
        return jsonify({"error": "Product not found"}), 404

    user_id = session["user"]["id"]

    # Prevent duplicate reports from same user on same product
    existing = db.reports.find_one({
        "product_id": product_id,
        "reported_by": user_id,
    })
    if existing:
        return jsonify({"error": "You have already reported this listing"}), 409

    db.reports.insert_one({
        "product_id": product_id,
        "product_name": product.get("name", ""),
        "reported_by": user_id,
        "reporter_name": session["user"]["name"],
        "reason": reason,
        "details": details,
        "status": "pending",
        "created_at": datetime.utcnow(),
    })

    return jsonify({"success": True, "message": "Report submitted successfully"})


@reports_bp.route("/api/reports/reasons", methods=["GET"])
def get_reasons():
    """Return list of valid report reasons."""
    return jsonify(VALID_REASONS)
