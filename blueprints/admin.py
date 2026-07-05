"""
Admin Blueprint – dashboard, product approval, user management, daily report.
"""
from flask import Blueprint, request, jsonify, session, render_template
from bson import ObjectId
from bson.errors import InvalidId
from utils.db import get_db
from utils.decorators import admin_required
from utils.cloudinary_utils import delete_image
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__)


def serialize_doc(doc):
    """Convert ObjectId fields to strings."""
    doc["_id"] = str(doc["_id"])
    for key in ["seller_id", "reported_by"]:
        if key in doc and doc[key]:
            doc[key] = str(doc[key])
    for field in ["created_at", "updated_at", "added_at"]:
        if field in doc and doc[field]:
            doc[field] = doc[field].isoformat()
    return doc


# ──────────────────────────────────────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/admin")
@admin_bp.route("/admin/dashboard")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")


@admin_bp.route("/admin/products")
@admin_required
def products_page():
    return render_template("admin/products.html")


@admin_bp.route("/admin/students")
@admin_required
def students_page():
    return render_template("admin/students.html")


@admin_bp.route("/admin/daily-report")
@admin_required
def daily_report_page():
    return render_template("admin/daily_report.html")


# ──────────────────────────────────────────────────────────────────────────────
# Stats API
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/stats", methods=["GET"])
@admin_required
def get_stats():
    """Return dashboard statistics."""
    db = get_db()

    total_students = db.users.count_documents({})
    total_products = db.products.count_documents({})
    active_products = db.products.count_documents({"status": "approved"})
    sold_products = db.products.count_documents({"status": "sold"})
    pending_products = db.products.count_documents({"status": "pending"})
    rejected_products = db.products.count_documents({"status": "rejected"})

    # Category distribution
    pipeline = [
        {"$match": {"status": {"$in": ["approved", "sold"]}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    category_data = list(db.products.aggregate(pipeline))

    # Monthly listings (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_pipeline = [
        {"$match": {"created_at": {"$gte": six_months_ago}}},
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$created_at"},
                    "month": {"$month": "$created_at"},
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    monthly_data = list(db.products.aggregate(monthly_pipeline))

    return jsonify({
        "total_students": total_students,
        "total_products": total_products,
        "active_products": active_products,
        "sold_products": sold_products,
        "pending_products": pending_products,
        "rejected_products": rejected_products,
        "category_data": [{"category": r["_id"], "count": r["count"]} for r in category_data],
        "monthly_data": [
            {
                "month": f"{r['_id']['year']}-{r['_id']['month']:02d}",
                "count": r["count"],
            }
            for r in monthly_data
        ],
    })


# ──────────────────────────────────────────────────────────────────────────────
# Product Management
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/products", methods=["GET"])
@admin_required
def get_all_products():
    """List all products with optional filters."""
    db = get_db()
    query = {}

    status = request.args.get("status", "")
    if status:
        query["status"] = status

    q = request.args.get("q", "").strip()
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"seller_name": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
        ]

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(50, int(request.args.get("limit", 20)))
    except ValueError:
        page, limit = 1, 20

    skip = (page - 1) * limit
    total = db.products.count_documents(query)
    products = list(
        db.products.find(query).sort("created_at", -1).skip(skip).limit(limit)
    )

    return jsonify({
        "products": [serialize_doc(p) for p in products],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    })


@admin_bp.route("/api/admin/products/<product_id>/approve", methods=["PATCH"])
@admin_required
def approve_product(product_id):
    """Approve a pending product."""
    db = get_db()
    try:
        db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"status": "approved", "updated_at": datetime.utcnow()}},
        )
    except InvalidId:
        return jsonify({"error": "Invalid ID"}), 400

    return jsonify({"success": True, "message": "Product approved"})


@admin_bp.route("/api/admin/products/<product_id>/reject", methods=["PATCH"])
@admin_required
def reject_product(product_id):
    """Reject a pending product."""
    db = get_db()
    data = request.get_json() or {}
    reason = data.get("reason", "")
    try:
        db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {
                "status": "rejected",
                "rejection_reason": reason,
                "updated_at": datetime.utcnow(),
            }},
        )
    except InvalidId:
        return jsonify({"error": "Invalid ID"}), 400

    return jsonify({"success": True, "message": "Product rejected"})


@admin_bp.route("/api/admin/products/<product_id>", methods=["DELETE"])
@admin_required
def admin_delete_product(product_id):
    """Admin delete any product."""
    db = get_db()
    try:
        p = db.products.find_one({"_id": ObjectId(product_id)})
    except InvalidId:
        return jsonify({"error": "Invalid ID"}), 400

    if not p:
        return jsonify({"error": "Product not found"}), 404

    for img in p.get("images", []):
        delete_image(img.get("public_id", ""))

    db.products.delete_one({"_id": ObjectId(product_id)})
    db.wishlists.delete_many({"product_id": product_id})
    db.reports.delete_many({"product_id": product_id})

    return jsonify({"success": True, "message": "Product deleted"})


@admin_bp.route("/api/admin/products/<product_id>/sold", methods=["PATCH"])
@admin_required
def admin_mark_sold(product_id):
    """Admin mark product as sold."""
    db = get_db()
    try:
        db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"status": "sold", "updated_at": datetime.utcnow()}},
        )
    except InvalidId:
        return jsonify({"error": "Invalid ID"}), 400
    return jsonify({"success": True})


# ──────────────────────────────────────────────────────────────────────────────
# Student Management
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/students", methods=["GET"])
@admin_required
def get_all_students():
    """List all students."""
    db = get_db()

    q = request.args.get("q", "").strip()
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"department": {"$regex": q, "$options": "i"}},
        ]

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(50, int(request.args.get("limit", 20)))
    except ValueError:
        page, limit = 1, 20

    skip = (page - 1) * limit
    total = db.users.count_documents(query)
    students = list(
        db.users.find(query, {"google_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    return jsonify({
        "students": [serialize_doc(s) for s in students],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    })


@admin_bp.route("/api/admin/students/<student_id>", methods=["DELETE"])
@admin_required
def delete_student(student_id):
    """Delete a student and all their products."""
    db = get_db()
    try:
        student = db.users.find_one({"_id": ObjectId(student_id)})
    except InvalidId:
        return jsonify({"error": "Invalid ID"}), 400

    if not student:
        return jsonify({"error": "Student not found"}), 404

    # Delete all products by student
    student_products = list(db.products.find({"seller_id": ObjectId(student_id)}))
    for p in student_products:
        for img in p.get("images", []):
            delete_image(img.get("public_id", ""))
    db.products.delete_many({"seller_id": ObjectId(student_id)})
    db.wishlists.delete_many({"user_id": student_id})
    db.reports.delete_many({"reported_by": student_id})
    db.users.delete_one({"_id": ObjectId(student_id)})

    return jsonify({"success": True, "message": "Student deleted"})


# ──────────────────────────────────────────────────────────────────────────────
# Reports
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/reports", methods=["GET"])
@admin_required
def get_reports():
    """List all product reports."""
    db = get_db()
    reports = list(db.reports.find().sort("created_at", -1).limit(100))
    return jsonify([serialize_doc(r) for r in reports])


@admin_bp.route("/api/admin/reports/<report_id>", methods=["PATCH"])
@admin_required
def resolve_report(report_id):
    """Mark a report as resolved."""
    db = get_db()
    try:
        db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": {"status": "resolved"}},
        )
    except InvalidId:
        return jsonify({"error": "Invalid ID"}), 400
    return jsonify({"success": True})


# ──────────────────────────────────────────────────────────────────────────────
# Daily Report
# ──────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/api/admin/daily-report", methods=["GET"])
@admin_required
def daily_report_data():
    """Generate data for the daily report."""
    db = get_db()
    date_str = request.args.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    try:
        report_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        report_date = datetime.utcnow()

    next_day = report_date + timedelta(days=1)

    # New users today
    new_users = db.users.count_documents({
        "created_at": {"$gte": report_date, "$lt": next_day}
    })

    # Products added today
    products_added = db.products.count_documents({
        "created_at": {"$gte": report_date, "$lt": next_day}
    })

    # Products sold today
    products_sold = db.products.count_documents({
        "status": "sold",
        "updated_at": {"$gte": report_date, "$lt": next_day},
    })

    # Active listings total
    active_listings = db.products.count_documents({"status": "approved"})

    # Deleted today (we track via a soft-delete or count from reports resolved)
    deleted_today = db.reports.count_documents({
        "status": "resolved",
        "created_at": {"$gte": report_date, "$lt": next_day},
    })

    # Category breakdown (all active)
    cat_pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cat_data = list(db.products.aggregate(cat_pipeline))

    return jsonify({
        "date": date_str,
        "new_users": new_users,
        "products_added": products_added,
        "products_sold": products_sold,
        "active_listings": active_listings,
        "deleted_today": deleted_today,
        "category_breakdown": [
            {"category": r["_id"] or "Unknown", "count": r["count"]}
            for r in cat_data
        ],
        "total_students": db.users.count_documents({}),
        "total_products": db.products.count_documents({}),
    })
