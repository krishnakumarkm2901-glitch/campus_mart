"""
Auth decorators for protecting routes.
"""
from functools import wraps
from flask import session, redirect, url_for, jsonify, request


def login_required(f):
    """Require student to be logged in via Google."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Require admin to be logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            if request.is_json or request.path.startswith("/api/admin"):
                return jsonify({"error": "Admin access required"}), 403
            return redirect(url_for("auth.admin_login_page"))
        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    """JSON-only version – always returns 401 JSON."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated
