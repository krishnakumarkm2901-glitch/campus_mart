"""Migrate MongoDB data from a local MongoDB instance to MongoDB Atlas.

Usage:
    python migrate_to_atlas.py

Environment variables:
    LOCAL_MONGO_URI   - local MongoDB connection string
    ATLAS_MONGO_URI   - MongoDB Atlas connection string
"""

import os
import sys
from typing import Dict, Any

from dotenv import load_dotenv
from pymongo import MongoClient, errors
from pymongo.operations import IndexModel

load_dotenv()

LOCAL_MONGO_URI = os.getenv("LOCAL_MONGO_URI")
ATLAS_MONGO_URI = os.getenv("ATLAS_MONGO_URI")
SKIP_DATABASES = {"admin", "local", "config"}


def fatal(message: str, error: Exception = None) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    if error:
        print(repr(error), file=sys.stderr)
    sys.exit(1)


def connect(uri: str, label: str) -> MongoClient:
    try:
        client = MongoClient(uri)
        client.admin.command("ping")
        print(f"Connected to {label} MongoDB successfully.")
        return client
    except errors.PyMongoError as exc:
        fatal(f"Unable to connect to {label} MongoDB.", exc)


def build_index_models(index_info: Dict[str, Dict[str, Any]]) -> list[IndexModel]:
    models = []
    for name, info in index_info.items():
        if name == "_id_":
            continue

        keys = info.get("key")
        if not keys:
            continue

        kwargs: Dict[str, Any] = {}
        for opt in [
            "unique",
            "sparse",
            "expireAfterSeconds",
            "partialFilterExpression",
            "collation",
            "default_language",
            "language_override",
            "weights",
            "background",
        ]:
            if opt in info:
                kwargs[opt] = info[opt]

        models.append(IndexModel(keys, **kwargs))
    return models


def copy_collection(src_db, dst_db, collection_name: str) -> dict[str, Any]:
    src_coll = src_db[collection_name]
    dst_coll = dst_db[collection_name]

    print(f"  Migrating collection: {collection_name}")

    try:
        index_info = src_coll.index_information()
        models = build_index_models(index_info)
        if models:
            dst_coll.create_indexes(models)
            print(f"    Created/ensured {len(models)} indexes.")
    except errors.PyMongoError as exc:
        print(f"    Warning: failed to sync indexes for {collection_name}: {exc}")

    total_documents = src_coll.count_documents({})
    if total_documents == 0:
        print("    No documents to migrate.")
        return {"copied": 0, "skipped": 0, "errors": 0}

    copied = 0
    skipped = 0
    errors_count = 0
    progress_step = max(total_documents // 20, 1)

    for idx, document in enumerate(src_coll.find({}), start=1):
        try:
            dst_coll.replace_one({"_id": document["_id"]}, document, upsert=True)
            copied += 1
        except errors.DuplicateKeyError:
            skipped += 1
        except errors.PyMongoError as exc:
            errors_count += 1
            print(f"    Error migrating document {_short_id(document)}: {exc}")

        if idx % progress_step == 0 or idx == total_documents:
            print(f"    Progress: {idx}/{total_documents} documents processed.")

    return {"copied": copied, "skipped": skipped, "errors": errors_count}


def _short_id(document: dict[str, Any]) -> str:
    return str(document.get("_id", "<unknown>"))[:14]


def migrate_database(src_client: MongoClient, dst_client: MongoClient, db_name: str) -> dict[str, Any]:
    print(f"Migrating database: {db_name}")
    src_db = src_client[db_name]
    dst_db = dst_client[db_name]

    collections = [name for name in src_db.list_collection_names() if not name.startswith("system.")]
    if not collections:
        print("  No collections found.")
        return {"collections": 0, "copied": 0, "skipped": 0, "errors": 0}

    result = {"collections": 0, "copied": 0, "skipped": 0, "errors": 0}
    for collection_name in collections:
        collection_result = copy_collection(src_db, dst_db, collection_name)
        result["collections"] += 1
        result["copied"] += collection_result["copied"]
        result["skipped"] += collection_result["skipped"]
        result["errors"] += collection_result["errors"]

    return result


def summarize(summary: dict[str, Any]) -> None:
    print("\nMigration summary")
    print("-----------------")
    print(f"Databases migrated: {summary.get('databases', 0)}")
    print(f"Collections migrated: {summary.get('collections', 0)}")
    print(f"Documents copied: {summary.get('copied', 0)}")
    print(f"Documents skipped: {summary.get('skipped', 0)}")
    print(f"Errors: {summary.get('errors', 0)}")


def main() -> int:
    if not LOCAL_MONGO_URI:
        fatal("LOCAL_MONGO_URI environment variable is missing.")
    if not ATLAS_MONGO_URI:
        fatal("ATLAS_MONGO_URI environment variable is missing.")

    local_client = connect(LOCAL_MONGO_URI, "local")
    atlas_client = connect(ATLAS_MONGO_URI, "Atlas")

    database_names = [
        db_name
        for db_name in local_client.list_database_names()
        if db_name not in SKIP_DATABASES
    ]

    if not database_names:
        fatal("No user databases found in the local MongoDB instance.")

    summary = {"databases": 0, "collections": 0, "copied": 0, "skipped": 0, "errors": 0}

    for db_name in sorted(database_names):
        db_result = migrate_database(local_client, atlas_client, db_name)
        summary["databases"] += 1
        summary["collections"] += db_result["collections"]
        summary["copied"] += db_result["copied"]
        summary["skipped"] += db_result["skipped"]
        summary["errors"] += db_result["errors"]

    summarize(summary)
    print("\nMigration complete. Local data remains unchanged.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Migration cancelled by user.")
        raise
