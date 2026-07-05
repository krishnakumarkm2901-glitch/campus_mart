"""
CampusMart – Flask Application Entry Point
"""
from flask import Flask, render_template, session, redirect, url_for
from flask_cors import CORS
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from utils.db import close_db, init_db_indexes
from blueprints.auth import auth_bp
from blueprints.products import products_bp
from blueprints.admin import admin_bp
from blueprints.wishlist import wishlist_bp
from blueprints.reports import reports_bp
from blueprints.contact import contact_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Fix proxy headers from Render so request.host_url matches the deployed URL.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Extensions
    CORS(app)
    Session(app)

    # Teardown
    app.teardown_appcontext(close_db)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(contact_bp)

    # ──────────────────────────────────
    # Main page routes (render templates)
    # ───────────────────────────────────

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/product/<product_id>")
    def product_detail(product_id):
        return render_template("product_detail.html", product_id=product_id)

    @app.route("/sell")
    def sell():
        if "user" not in session:
            return redirect(url_for("auth.login_page"))
        return render_template("sell.html")

    @app.route("/sell/edit/<product_id>")
    def edit_product(product_id):
        if "user" not in session:
            return redirect(url_for("auth.login_page"))
        return render_template("sell.html", product_id=product_id, editing=True)

    @app.route("/categories")
    def categories():
        return render_template("categories.html")

    @app.route("/search")
    def search():
        return render_template("search.html")

    @app.route("/wishlist")
    def wishlist():
        if "user" not in session:
            return redirect(url_for("auth.login_page"))
        return render_template("wishlist.html")
    

    @app.route("/my-listings")
    def my_listings():
        if "user" not in session:
            return redirect(url_for("auth.login_page"))
        return render_template("my_listings.html")

    @app.route("/profile")
    def profile():
        if "user" not in session:
            return redirect(url_for("auth.login_page"))
        return render_template("profile.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/contact")
    def contact():
        return render_template(
            "contact.html",
            support_email=app.config["CONTACT_EMAIL"] or "support@campusmart.edu",
        )

    # ───────────────────────────────────────────────
    # Context processor – expose session to templates
    # ───────────────────────────────────────────────

    @app.context_processor
    def inject_user():
        return {
            "current_user": session.get("user"),
            "is_admin": session.get("is_admin", False),
        }

    # ───────────────
    # Error handlers
    # ───────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template("index.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("index.html"), 500

    # Register the main blueprint for clarity
    app.add_url_rule("/", "main.home", home)

    return app


app = create_app()

if __name__ == "__main__":
    init_db_indexes(app)
    app.run(debug=app.config["DEBUG"], host="0.0.0.0", port=5000)
