"""
Wishlist Blueprint – save/unsave products.
"""
from flask import Blueprint, jsonify, session
from bson import ObjectId
from utils.db import get_db
from utils.decorators import api_login_required
from datetime import datetime

wishlist_bp = Blueprint("wishlist", __name__)


@wishlist_bp.route("/api/wishlist", methods=["GET"])
@api_login_required
def get_wishlist():
    """Return the current user's wishlist with product details."""
    db = get_db()
    user_id = session["user"]["id"]

    wishlist_items = list(db.wishlists.find({"user_id": user_id}))
    product_ids = [ObjectId(item["product_id"]) for item in wishlist_items]

    products = list(
        db.products.find({"_id": {"$in": product_ids}, "status": "approved"})
    )

    result = []
    for p in products:
        p["_id"] = str(p["_id"])
        p["seller_id"] = str(p.get("seller_id", ""))
        result.append(p)

    return jsonify(result)


@wishlist_bp.route("/api/wishlist/<product_id>", methods=["POST"])
@api_login_required
def add_to_wishlist(product_id):
    """Add a product to wishlist."""
    db = get_db()
    user_id = session["user"]["id"]

    # Check product exists
    try:
        product = db.products.find_one({"_id": ObjectId(product_id)})
    except Exception:
        return jsonify({"error": "Invalid product ID"}), 400

    if not product:
        return jsonify({"error": "Product not found"}), 404

    try:
        db.wishlists.insert_one({
            "user_id": user_id,
            "product_id": product_id,
            "added_at": datetime.utcnow(),
        })
        return jsonify({"success": True, "message": "Added to wishlist"})
    except Exception:
        return jsonify({"error": "Already in wishlist"}), 409


@wishlist_bp.route("/api/wishlist/<product_id>", methods=["DELETE"])
@api_login_required
def remove_from_wishlist(product_id):
    """Remove a product from wishlist."""
    db = get_db()
    user_id = session["user"]["id"]

    result = db.wishlists.delete_one({
        "user_id": user_id,
        "product_id": product_id,
    })

    if result.deleted_count == 0:
        return jsonify({"error": "Not in wishlist"}), 404

    return jsonify({"success": True, "message": "Removed from wishlist"})


@wishlist_bp.route("/api/wishlist/check/<product_id>", methods=["GET"])
@api_login_required
def check_wishlist(product_id):
    """Check if a product is in the user's wishlist."""
    db = get_db()
    user_id = session["user"]["id"]

    item = db.wishlists.find_one({
        "user_id": user_id,
        "product_id": product_id,
    })

    return jsonify({"in_wishlist": item is not None})
