"""
Products Blueprint – full CRUD for product listings.
"""
from flask import Blueprint, request, jsonify, session, render_template
from bson import ObjectId
from bson.errors import InvalidId
from utils.db import get_db
from utils.decorators import api_login_required
from utils.cloudinary_utils import upload_multiple, delete_image
from datetime import datetime

products_bp = Blueprint("products", __name__)

CATEGORIES = [
    "Engineering Books",
    "Lab Coats",
    "Scientific Calculators",
    "Drawing Instruments",
]

CONDITIONS = ["New", "Like New", "Good", "Fair", "Used"]
STATUSES = ["pending", "approved", "rejected", "sold"]


def serialize_product(p):
    """Convert MongoDB product doc to JSON-serializable dict."""
    p["_id"] = str(p["_id"])
    p["seller_id"] = str(p.get("seller_id", ""))
    if "created_at" in p:
        p["created_at"] = p["created_at"].isoformat()
    if "updated_at" in p:
        p["updated_at"] = p["updated_at"].isoformat()
    return p


# ──────────────────────────────────────────────────────────────────────────────
# List / Search Products
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/products", methods=["GET"])
def list_products():
    """
    Get approved products with optional filters and sorting.
    Query params: q, category, condition, department, min_price, max_price,
                  sort (newest|oldest|price_asc|price_desc), page, limit
    """
    db = get_db()
    query = {"status": "approved"}

    # Text search
    q = request.args.get("q", "").strip()
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
        ]

    # Filters
    category = request.args.get("category", "")
    if category:
        query["category"] = category

    condition = request.args.get("condition", "")
    if condition:
        query["condition"] = condition

    department = request.args.get("department", "")
    if department:
        query["department"] = {"$regex": department, "$options": "i"}

    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")
    price_filter = {}
    if min_price:
        try:
            price_filter["$gte"] = float(min_price)
        except ValueError:
            pass
    if max_price:
        try:
            price_filter["$lte"] = float(max_price)
        except ValueError:
            pass
    if price_filter:
        query["price"] = price_filter

    # Sorting
    sort_map = {
        "newest": [("created_at", -1)],
        "oldest": [("created_at", 1)],
        "price_asc": [("price", 1)],
        "price_desc": [("price", -1)],
    }
    sort = request.args.get("sort", "newest")
    sort_order = sort_map.get(sort, [("created_at", -1)])

    # Pagination
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(50, max(1, int(request.args.get("limit", 12))))
    except ValueError:
        page, limit = 1, 12

    skip = (page - 1) * limit
    total = db.products.count_documents(query)
    products = list(db.products.find(query).sort(sort_order).skip(skip).limit(limit))

    return jsonify({
        "products": [serialize_product(p) for p in products],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "limit": limit,
    })


@products_bp.route("/api/products/featured", methods=["GET"])
def featured_products():
    """Return featured (recently approved) products."""
    db = get_db()
    products = list(
        db.products.find({"status": "approved"})
        .sort("created_at", -1)
        .limit(8)
    )
    return jsonify([serialize_product(p) for p in products])


@products_bp.route("/api/products/categories-count", methods=["GET"])
def categories_count():
    """Return product count per category."""
    db = get_db()
    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
    ]
    result = list(db.products.aggregate(pipeline))
    counts = {r["_id"]: r["count"] for r in result if r["_id"]}
    return jsonify(counts)


# ──────────────────────────────────────────────────────────────────────────────
# Single Product
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/products/<product_id>", methods=["GET"])
def get_product(product_id):
    """Get a single product by ID."""
    db = get_db()
    try:
        p = db.products.find_one({"_id": ObjectId(product_id)})
    except InvalidId:
        return jsonify({"error": "Invalid product ID"}), 400

    if not p:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(serialize_product(p))


# ──────────────────────────────────────────────────────────────────────────────
# Create Product
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/products", methods=["POST"])
@api_login_required
def create_product():
    """Create a new product listing (status=pending until admin approves)."""
    db = get_db()
    user = session["user"]

    # Validate required text fields
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "")
    description = request.form.get("description", "").strip()
    price_str = request.form.get("price", "")
    condition = request.form.get("condition", "")
    department = request.form.get("department", "").strip()
    pickup_location = request.form.get("pickup_location", "").strip()
    phone = request.form.get("phone", "").strip() or user.get("phone", "")

    errors = {}
    if not name:
        errors["name"] = "Product name is required"
    if category not in CATEGORIES:
        errors["category"] = f"Invalid category"
    if not description:
        errors["description"] = "Description is required"
    if condition not in CONDITIONS:
        errors["condition"] = "Invalid condition"
    if not department:
        errors["department"] = "Department is required"

    try:
        price = float(price_str)
        if price < 0:
            errors["price"] = "Price must be non-negative"
    except (ValueError, TypeError):
        errors["price"] = "Valid price is required"

    if errors:
        return jsonify({"errors": errors}), 422

    # Upload images
    images = []
    files = request.files.getlist("images")
    if files and files[0].filename:
        try:
            images = upload_multiple(files)
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 500

    product = {
        "seller_id": ObjectId(user["id"]),
        "seller_name": user["name"],
        "seller_email": user["email"],
        "seller_photo": user.get("profile_photo", ""),
        "name": name,
        "category": category,
        "description": description,
        "price": price,
        "condition": condition,
        "department": department,
        "pickup_location": pickup_location,
        "phone": phone,
        "images": images,  # [{url, public_id}]
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = db.products.insert_one(product)
    product["_id"] = result.inserted_id
    return jsonify(serialize_product(product)), 201


# ──────────────────────────────────────────────────────────────────────────────
# Update Product
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/products/<product_id>", methods=["PUT"])
@api_login_required
def update_product(product_id):
    """Edit a product (owner only). Re-sets status to pending for re-approval."""
    db = get_db()
    user = session["user"]

    try:
        p = db.products.find_one({"_id": ObjectId(product_id)})
    except InvalidId:
        return jsonify({"error": "Invalid product ID"}), 400

    if not p:
        return jsonify({"error": "Product not found"}), 404

    if str(p["seller_id"]) != user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    data = request.form or request.get_json() or {}
    update = {"updated_at": datetime.utcnow(), "status": "pending"}

    editable = ["name", "description", "price", "condition", "department",
                "pickup_location", "phone", "category"]
    for field in editable:
        if field in data:
            val = data[field]
            if field == "price":
                try:
                    val = float(val)
                except ValueError:
                    continue
            update[field] = val

    # Handle new images
    files = request.files.getlist("images") if hasattr(request, "files") else []
    if files and files[0].filename:
        # Delete old images from Cloudinary
        for img in p.get("images", []):
            delete_image(img.get("public_id", ""))
        try:
            update["images"] = upload_multiple(files)
        except RuntimeError as e:
            return jsonify({"error": str(e)}), 500

    db.products.update_one({"_id": ObjectId(product_id)}, {"$set": update})
    updated = db.products.find_one({"_id": ObjectId(product_id)})
    return jsonify(serialize_product(updated))


# ──────────────────────────────────────────────────────────────────────────────
# Delete Product
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/products/<product_id>", methods=["DELETE"])
@api_login_required
def delete_product(product_id):
    """Delete a product (owner or admin)."""
    db = get_db()
    user = session["user"]

    try:
        p = db.products.find_one({"_id": ObjectId(product_id)})
    except InvalidId:
        return jsonify({"error": "Invalid product ID"}), 400

    if not p:
        return jsonify({"error": "Product not found"}), 404

    is_owner = str(p["seller_id"]) == user["id"]
    is_admin = session.get("is_admin", False)

    if not is_owner and not is_admin:
        return jsonify({"error": "Not authorized"}), 403

    # Clean up Cloudinary images
    for img in p.get("images", []):
        delete_image(img.get("public_id", ""))

    db.products.delete_one({"_id": ObjectId(product_id)})
    db.wishlists.delete_many({"product_id": product_id})
    db.reports.delete_many({"product_id": product_id})

    return jsonify({"success": True, "message": "Product deleted"})


# ──────────────────────────────────────────────────────────────────────────────
# Mark as Sold
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/products/<product_id>/sold", methods=["PATCH"])
@api_login_required
def mark_sold(product_id):
    """Mark a product as sold (owner only)."""
    db = get_db()
    user = session["user"]

    try:
        p = db.products.find_one({"_id": ObjectId(product_id)})
    except InvalidId:
        return jsonify({"error": "Invalid product ID"}), 400

    if not p:
        return jsonify({"error": "Product not found"}), 404

    if str(p["seller_id"]) != user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"status": "sold", "updated_at": datetime.utcnow()}},
    )

    return jsonify({"success": True, "message": "Marked as sold"})


# ──────────────────────────────────────────────────────────────────────────────
# My Listings
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/my-listings", methods=["GET"])
@api_login_required
def my_listings():
    """Get the current user's own product listings."""
    db = get_db()
    user_id = session["user"]["id"]

    products = list(
        db.products.find({"seller_id": ObjectId(user_id)}).sort("created_at", -1)
    )
    return jsonify([serialize_product(p) for p in products])


# ──────────────────────────────────────────────────────────────────────────────
# Static Data
# ──────────────────────────────────────────────────────────────────────────────

@products_bp.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(CATEGORIES)


@products_bp.route("/api/conditions", methods=["GET"])
def get_conditions():
    return jsonify(CONDITIONS)
