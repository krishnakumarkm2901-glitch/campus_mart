"""
Database utility – creates and caches the MongoDB connection.
"""
from urllib.parse import urlparse

from flask import current_app, g
from pymongo import ASCENDING, TEXT, MongoClient, errors


def _get_database_name(config=None):
    if config is None:
        config = current_app.config

    configured_name = config.get("MONGO_DB_NAME")
    if configured_name:
        return configured_name

    uri = config.get("MONGO_URI", "")
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
            g.db = client[_get_database_name(current_app.config)]
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
        db_name = _get_database_name(app.config)
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


def _index_keys(index):
    """Return an index key specification as a list of (field, direction) pairs."""
    return list(index.get("key", {}).items())


def _text_index_fields(index):
    """Return the fields covered by a text index, or an empty set."""
    weights = index.get("weights")
    if weights:
        return set(weights)

    return {
        field
        for field, direction in _index_keys(index)
        if direction == TEXT or direction == "text"
    }


def _ensure_index(collection, keys, logger, *, name=None, **options):
    """Create one non-text index only when its specification is not present."""
    requested_keys = list(keys) if not isinstance(keys, str) else [(keys, ASCENDING)]
    try:
        indexes = list(collection.list_indexes())

        for index in indexes:
            existing_name = index.get("name")
            if _index_keys(index) == requested_keys:
                differing_options = {
                    option: (index.get(option), value)
                    for option, value in options.items()
                    if index.get(option, False) != value
                }
                if differing_options:
                    logger.warning(
                        "MongoDB index %s.%s has the requested keys but "
                        "different options %s; leaving it unchanged",
                        collection.name,
                        existing_name,
                        differing_options,
                    )
                else:
                    logger.info(
                        "Skipping existing MongoDB index %s.%s",
                        collection.name,
                        existing_name,
                    )
                return existing_name

            if name and existing_name == name:
                logger.warning(
                    "MongoDB index %s.%s exists with a different specification; "
                    "leaving it unchanged",
                    collection.name,
                    name,
                )
                return existing_name

        created_name = collection.create_index(
            requested_keys, name=name, **options
        )
        logger.info(
            "Created MongoDB index %s.%s", collection.name, created_name
        )
        return created_name
    except errors.PyMongoError as exc:
        logger.error(
            "Could not ensure MongoDB index %s on %s: %s",
            name or requested_keys,
            collection.name,
            exc,
        )
        return None


def _ensure_text_index(collection, keys, logger, *, name, **options):
    """Ensure a text index without attempting to create a second text index."""
    requested_keys = list(keys)
    requested_fields = {
        field
        for field, direction in requested_keys
        if direction == TEXT or direction == "text"
    }

    try:
        for index in collection.list_indexes():
            existing_fields = _text_index_fields(index)
            if not existing_fields:
                continue

            existing_name = index.get("name")
            if existing_fields == requested_fields:
                logger.info(
                    "Skipping existing equivalent MongoDB text index %s.%s "
                    "(requested name: %s)",
                    collection.name,
                    existing_name,
                    name,
                )
            else:
                logger.warning(
                    "MongoDB collection %s already has text index %s on fields "
                    "%s; required index %s uses fields %s. Leaving the existing "
                    "text index unchanged because MongoDB permits only one text "
                    "index per collection",
                    collection.name,
                    existing_name,
                    sorted(existing_fields),
                    name,
                    sorted(requested_fields),
                )
            return existing_name

        created_name = collection.create_index(
            requested_keys, name=name, **options
        )
        logger.info(
            "Created MongoDB text index %s.%s", collection.name, created_name
        )
        return created_name
    except errors.PyMongoError as exc:
        logger.error(
            "Could not ensure MongoDB text index %s on %s: %s",
            name,
            collection.name,
            exc,
        )
        return None


def init_db_indexes(app):
    """Idempotently create application indexes without blocking startup."""
    client = None
    try:
        client = _create_mongo_client(app.config["MONGO_URI"])
        client.admin.command("ping")
        db = client[_get_database_name(app.config)]

        # Products indexes
        _ensure_text_index(
            db.products,
            [("name", TEXT), ("description", TEXT), ("category", TEXT)],
            app.logger,
            name="product_text_search",
        )
        _ensure_index(db.products, "department", app.logger)
        _ensure_index(db.products, "category", app.logger)
        _ensure_index(db.products, "status", app.logger)
        _ensure_index(db.products, "seller_id", app.logger)
        _ensure_index(db.products, "created_at", app.logger)

        # Users indexes
        _ensure_index(db.users, "google_id", app.logger, unique=True)
        _ensure_index(db.users, "email", app.logger, unique=True)

        # Reports indexes
        _ensure_index(db.reports, "product_id", app.logger)

        # Wishlist indexes
        _ensure_index(
            db.wishlists,
            [("user_id", ASCENDING), ("product_id", ASCENDING)],
            app.logger,
            unique=True,
        )

        # Contact message indexes
        _ensure_index(db.contact_messages, "created_at", app.logger)
        _ensure_index(db.contact_messages, "status", app.logger)
        _ensure_index(db.contact_messages, "email_status", app.logger)
    except errors.PyMongoError as exc:
        app.logger.error("Failed to initialize MongoDB indexes: %s", exc)
    finally:
        if client is not None:
            client.close()
