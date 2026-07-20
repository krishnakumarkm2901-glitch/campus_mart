"""
Authentication Blueprint
Handles Google OAuth for students and username/password for admin.
"""
import ipaddress
import json
import os
from copy import deepcopy
from urllib.parse import urlsplit
import requests as http_requests
from flask import (
    Blueprint, redirect, request, session, url_for,
    render_template, flash, current_app, jsonify
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from utils.db import get_db
from datetime import datetime

auth_bp = Blueprint("auth", __name__)

# Allow HTTP for local dev (remove in production)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": None,
        "client_secret": None,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [],
        "javascript_origins": ["http://localhost:5000"],
    }
}


def _is_local_host(hostname):
    if not hostname:
        return False
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_loopback
    except ValueError:
        return False


def _get_request_origin() -> str:
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    forwarded_host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host")

    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")

    return request.host_url.rstrip("/")


def get_effective_redirect_uri() -> str:
    """Return the redirect URI that should be used for the current request."""
    configured = current_app.config["GOOGLE_REDIRECT_URI"]
    callback = urlsplit(configured)
    callback_origin = f"{callback.scheme}://{callback.netloc}".rstrip("/")
    request_origin = _get_request_origin()

    if callback_origin.lower() != request_origin.lower():
        callback_host = callback.hostname
        request_host = urlsplit(request_origin).hostname
        if _is_local_host(callback_host):
            return configured
        if _is_local_host(request_host):
            return f"{request_origin}{url_for('auth.google_callback')}"

    return configured


def get_google_flow(state=None, code_verifier=None, redirect_uri=None):
    """Build the OAuth flow with current app config."""
    config = deepcopy(GOOGLE_CLIENT_CONFIG)
    config["web"]["client_id"] = current_app.config["GOOGLE_CLIENT_ID"]
    config["web"]["client_secret"] = current_app.config["GOOGLE_CLIENT_SECRET"]

    if redirect_uri is None:
        redirect_uri = get_effective_redirect_uri()

    config["web"]["redirect_uris"] = [redirect_uri]
    config["web"]["javascript_origins"] = [urlsplit(redirect_uri).scheme + "://" + urlsplit(redirect_uri).netloc]

    flow = Flow.from_client_config(
        config,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
        redirect_uri=redirect_uri,
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=code_verifier is None,
    )
    return flow


# ──────────────────────────────────────────────────────────────────────────────
# Student Auth
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login")
def login_page():
    """Render the student login page."""
    if session.get("user"):
        return redirect(url_for("main.home"))
    return render_template("login.html")


@auth_bp.route("/auth/google")
def google_login():
    """Redirect to Google's OAuth consent screen."""
    if not (
        current_app.config["GOOGLE_CLIENT_ID"]
        and current_app.config["GOOGLE_CLIENT_SECRET"]
        and current_app.config["GOOGLE_REDIRECT_URI"]
    ):
        flash(
            "Google login is not configured yet. Add GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI to the project's .env file, then restart the app.",
            "error",
        )
        return redirect(url_for("auth.login_page"))

    # OAuth cookies are scoped to a hostname. Use an effective redirect URI
    # depending on the configured callback and current request origin.
    callback = urlsplit(current_app.config["GOOGLE_REDIRECT_URI"])
    callback_origin = f"{callback.scheme}://{callback.netloc}".rstrip("/")
    request_origin = _get_request_origin()
    request_host = urlsplit(request_origin).hostname
    redirect_uri = get_effective_redirect_uri()

    if callback_origin.lower() != request_origin.lower():
        if _is_local_host(callback.hostname) and redirect_uri == current_app.config["GOOGLE_REDIRECT_URI"]:
            pass
        elif _is_local_host(request_host) and redirect_uri != current_app.config["GOOGLE_REDIRECT_URI"]:
            pass
        else:
            flash(
                "Google login is currently set up with a different callback URL. "
                "Update GOOGLE_REDIRECT_URI to your deployed app URL and add that URL to "
                "Google Cloud OAuth Authorized redirect URIs.",
                "error",
            )
            return redirect(url_for("auth.login_page"))

    flow = get_google_flow(redirect_uri=redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )
    # Keep a small set of attempts so a double-click or a second login tab
    # does not invalidate the first callback.
    attempts = session.get("oauth_attempts", {})
    attempts[state] = {
        "code_verifier": flow.code_verifier,
        "redirect_uri": redirect_uri,
    }
    while len(attempts) > 5:
        attempts.pop(next(iter(attempts)))
    session["oauth_attempts"] = attempts
    session.modified = True
    return redirect(authorization_url)


@auth_bp.route("/auth/google/callback")
def google_callback():
    """Handle Google's OAuth callback."""
    # Browsers can revisit the callback URL (refresh/back/restore).  A successful
    # callback consumes its one-time state, so replaying it must not show an
    # authentication error to a user who is already signed in.
    if session.get("user") and not session.get("oauth_attempts"):
        return redirect(url_for("main.home"))

    if "error" in request.args:
        flash("Google login was cancelled or failed.", "error")
        return redirect(url_for("auth.login_page"))

    try:
        received_state = request.args.get("state", "")
        attempts = session.get("oauth_attempts", {})
        state_data = attempts.get(received_state)
        if not received_state or not state_data:
            raise ValueError("Invalid or expired OAuth state. Please try signing in again.")

        code_verifier = state_data.get("code_verifier")
        redirect_uri = state_data.get("redirect_uri")
        if not code_verifier or not redirect_uri:
            raise ValueError("Invalid OAuth state data. Please try signing in again.")

        flow = get_google_flow(
            state=received_state,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            current_app.config["GOOGLE_CLIENT_ID"],
        )

        # Consume this attempt only after Google has accepted and verified it.
        attempts.pop(received_state, None)
        session["oauth_attempts"] = attempts
        session.modified = True
    except Exception as e:
        flash(f"Authentication failed: {str(e)}", "error")
        return redirect(url_for("auth.login_page"))

    # Validate email domain
    email = id_info.get("email", "")
    allowed_domain = current_app.config["ALLOWED_EMAIL_DOMAIN"]
    if allowed_domain != "*" and not email.endswith(allowed_domain):
        flash(
            f"Only {allowed_domain} email addresses are allowed. "
            "Please use your college email.",
            "error",
        )
        return redirect(url_for("auth.login_page"))

    # Upsert user in MongoDB
    db = get_db()
    google_id = id_info["sub"]
    user = db.users.find_one({"google_id": google_id})

    if not user:
        new_user = {
            "google_id": google_id,
            "name": id_info.get("name", ""),
            "email": email,
            "profile_photo": id_info.get("picture", ""),
            "department": "",
            "year": "",
            "phone": "",
            "created_at": datetime.utcnow(),
        }
        result = db.users.insert_one(new_user)
        new_user["_id"] = result.inserted_id
        user = new_user

    # Store in session as a persistent login.
    session.permanent = True
    session["user"] = {
        "id": str(user["_id"]),
        "google_id": google_id,
        "name": user["name"],
        "email": email,
        "profile_photo": user.get("profile_photo", ""),
        "department": user.get("department", ""),
        "year": user.get("year", ""),
        "phone": user.get("phone", ""),
    }

    return redirect(url_for("main.home"))


@auth_bp.route("/auth/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    response = redirect(url_for("auth.login_page"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Admin Auth
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/admin/login", methods=["GET"])
def admin_login_page():
    """Render the admin login page."""
    if session.get("is_admin"):
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html")


# Backwards-compatible alias: allow visiting `/loginadmin` to reach admin login.
@auth_bp.route("/loginadmin", methods=["GET"])
def loginadmin_page():
    """Alias route for admin login page at /loginadmin."""
    return admin_login_page()


@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    """Handle admin login."""
    data = request.get_json() or request.form
    username = data.get("username", "")
    password = data.get("password", "")

    if (
        username == current_app.config["ADMIN_USERNAME"]
        and password == current_app.config["ADMIN_PASSWORD"]
    ):
        session.permanent = True
        session["is_admin"] = True
        session["admin_name"] = username
        return jsonify({"success": True, "redirect": url_for("admin.dashboard")})

    return jsonify({"success": False, "error": "Invalid credentials"}), 401


@auth_bp.route("/admin/logout")
def admin_logout():
    """Log out the admin."""
    session.pop("is_admin", None)
    session.pop("admin_name", None)
    return redirect(url_for("auth.admin_login_page"))


# ──────────────────────────────────────────────────────────────────────────────
# Profile API
# ──────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/profile", methods=["GET"])
def get_profile():
    """Return current user profile."""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(user)


@auth_bp.route("/api/profile", methods=["PUT"])
def update_profile():
    """Update editable profile fields."""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    allowed = ["phone", "department", "year"]
    update = {k: data[k] for k in allowed if k in data}

    if not update:
        return jsonify({"error": "No valid fields to update"}), 400

    db = get_db()
    from bson import ObjectId
    db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update})

    # Refresh session
    for k, v in update.items():
        session["user"][k] = v
    session.modified = True

    return jsonify({"success": True, "user": session["user"]})
