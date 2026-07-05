"""
Database utility – creates and caches the MongoDB connection.
"""
from pymongo import MongoClient
from flask import current_app, g


def get_db():
    """Return the database instance, creating it if needed."""
    if "db" not in g:
        client = MongoClient(current_app.config["MONGO_URI"])
        g.db = client.get_default_database()
        g.mongo_client = client
    return g.db


def close_db(e=None):
    """Close the MongoDB connection at end of request."""
    client = g.pop("mongo_client", None)
    if client is not None:
        client.close()


def init_db_indexes(app):
    """Create indexes on startup for better query performance."""
    with app.app_context():
        client = MongoClient(app.config["MONGO_URI"])
        db = client.get_default_database()

        # Products indexes
        db.products.create_index([("name", "text"), ("description", "text")])
        db.products.create_index("category")
        db.products.create_index("status")
        db.products.create_index("seller_id")
        db.products.create_index("created_at")

        # Users indexes
        db.users.create_index("google_id", unique=True)
        db.users.create_index("email", unique=True)

        # Reports indexes
        db.reports.create_index("product_id")

        # Wishlist indexes
        db.wishlists.create_index([("user_id", 1), ("product_id", 1)], unique=True)

        # Contact message indexes
        db.contact_messages.create_index("created_at")
        db.contact_messages.create_index("status")
        db.contact_messages.create_index("email_status")

        client.close()
