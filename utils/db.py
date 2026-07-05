"""
Database utility – creates and caches the MongoDB connection.
"""
from urllib.parse import urlparse

from flask import current_app, g
from pymongo import MongoClient, errors


def _get_database_name():
    configured_name = current_app.config.get("MONGO_DB_NAME")
    if configured_name:
        return configured_name

    uri = current_app.config.get("MONGO_URI", "")
    parsed_uri = urlparse(uri)
    db_name = parsed_uri.path.lstrip("/")
    return db_name or "campusmart"


def _create_mongo_client(uri):
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_db():
    """Return the database instance, creating it if needed."""
    if "db" not in g:
        try:
            client = _create_mongo_client(current_app.config["MONGO_URI"])
            client.admin.command("ping")
            g.mongo_client = client
            g.db = client[_get_database_name()]
        except errors.PyMongoError as exc:
            raise RuntimeError(
                f"Unable to connect to MongoDB Atlas: {exc}"
            ) from exc
    return g.db


def close_db(e=None):
    """Close the MongoDB connection at end of request."""
    client = g.pop("mongo_client", None)
    if client is not None:
        client.close()


def log_db_startup(app):
    """Check the MongoDB Atlas connection and print startup information."""
    client = None
    try:
        client = _create_mongo_client(app.config["MONGO_URI"])
        client.admin.command("ping")
        db_name = _get_database_name()
        message = f"Connected to MongoDB Atlas database: {db_name}"
        print(message)
        app.logger.info(message)
    except errors.PyMongoError as exc:
        app.logger.error("MongoDB Atlas startup connection failed: %s", exc)
        raise RuntimeError(
            f"Unable to connect to MongoDB Atlas on startup: {exc}"
        ) from exc
    finally:
        if client is not None:
            client.close()


def init_db_indexes(app):
    """Create indexes on startup for better query performance."""
    client = None
    try:
        client = _create_mongo_client(app.config["MONGO_URI"])
        client.admin.command("ping")
        db = client[_get_database_name()]

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
    except errors.PyMongoError as exc:
        app.logger.error("Failed to initialize MongoDB indexes: %s", exc)
        raise
    finally:
        if client is not None:
            client.close()
