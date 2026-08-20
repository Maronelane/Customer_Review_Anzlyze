"""
MongoDB database for storing analysis results.
"""
import os
import uuid
from datetime import datetime, timezone

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

_client = None
_db = None


def _safe_for_mongo(value):
    """Convert nested data into MongoDB-safe values."""
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key == "model":
                continue
            cleaned[str(key)] = _safe_for_mongo(item)
        return cleaned
    if isinstance(value, list):
        return [_safe_for_mongo(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_for_mongo(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    return str(value)


def get_db():
    global _client, _db
    if _db is None:
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.environ.get("MONGODB_DB", "anzlyze")
        _client = MongoClient(uri)
        _db = _client[db_name]
    return _db


def init_mongo():
    db = get_db()
    db.analyses.create_index("created_at")
    db.results.create_index("analysis_id")
    db.predictions.create_index([("analysis_id", 1), ("sentiment", 1)])
    db.users.create_index("username", unique=True)
    db.progress.create_index("analysis_id", unique=True)


# ── User Auth ──


def create_user(username: str, password_hash: str) -> dict:
    db = get_db()
    user_id = str(uuid.uuid4())[:8]
    doc = {
        "_id": user_id,
        "username": username,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.users.insert_one(doc)
    return {"user_id": user_id, "username": username}


def get_user_by_username(username: str):
    db = get_db()
    return db.users.find_one({"username": username})


def get_user_by_id(user_id: str):
    db = get_db()
    return db.users.find_one({"_id": user_id}, {"password_hash": 0})


# ── Analysis ──


def create_analysis(filename: str, text_column: str, rating_column: str = None, stored_path: str = None, user_id: str = None) -> dict:
    db = get_db()
    analysis_id = str(uuid.uuid4())[:8]
    doc = {
        "_id": analysis_id,
        "filename": filename,
        "text_column": text_column,
        "rating_column": rating_column,
        "stored_path": stored_path,
        "user_id": user_id,
        "total_reviews": None,
        "status": "uploaded",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    db.analyses.insert_one(doc)
    return doc


def update_analysis_status(analysis_id: str, status: str, total_reviews: int = None):
    db = get_db()
    update = {"status": status}
    if total_reviews is not None:
        update["total_reviews"] = total_reviews
        update["completed_at"] = datetime.now(timezone.utc).isoformat()
    db.analyses.update_one({"_id": analysis_id}, {"$set": update})


def save_results(analysis_id: str, data: dict):
    db = get_db()
    doc = {
        "_id": str(uuid.uuid4())[:8],
        "analysis_id": analysis_id,
        "best_model": data.get("best_model"),
        "best_accuracy": data.get("best_accuracy"),
        "sentiment_distribution": _safe_for_mongo(data.get("sentiment_distribution")),
        "problems": _safe_for_mongo(data.get("problems")),
        "recommendations": _safe_for_mongo(data.get("recommendations")),
        "model_results": _safe_for_mongo(data.get("model_results")),
    }
    db.results.insert_one(doc)


def save_predictions(analysis_id: str, predictions: list[dict]):
    db = get_db()
    docs = [
        {
            "analysis_id": analysis_id,
            "review_text": p.get("text", p.get("review_text", ""))[:2000],
            "sentiment": p["sentiment"],
            "spam_score": p.get("spam_score", 0.0),
            "is_flagged": p.get("is_flagged", False),
            "cluster_id": p.get("cluster_id", -1),
            "cluster_label": p.get("cluster_label", ""),
        }
        for p in predictions
    ]
    if docs:
        db.predictions.insert_many(docs)


def get_analysis(analysis_id: str):
    db = get_db()
    doc = db.analyses.find_one({"_id": analysis_id})
    if doc:
        doc["id"] = doc.pop("_id")
    return doc


def get_results(analysis_id: str):
    db = get_db()
    doc = db.results.find_one({"analysis_id": analysis_id})
    return doc


def get_predictions(analysis_id: str, limit: int = 100, offset: int = 0, sentiment_filter: str = None, search_query: str = None):
    db = get_db()
    query = {"analysis_id": analysis_id}
    if sentiment_filter:
        query["sentiment"] = sentiment_filter
    if search_query:
        query["review_text"] = {"$regex": search_query, "$options": "i"}
    total = db.predictions.count_documents(query)
    rows = list(db.predictions.find(query, {"_id": 0}).sort("_id", 1).skip(offset).limit(limit))
    return {"predictions": rows, "total": total}


def list_analyses(user_id: str = None):
    db = get_db()
    query: dict = {"status": "completed"}
    if user_id:
        query["user_id"] = user_id
    docs = list(db.analyses.find(query).sort("created_at", -1))
    for doc in docs:
        doc["id"] = doc.pop("_id")
    return docs


# ── Progress Tracking ──


def set_progress(analysis_id: str, step: str, percent: int):
    db = get_db()
    db.progress.update_one(
        {"analysis_id": analysis_id},
        {"$set": {"step": step, "percent": percent, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )


def get_progress(analysis_id: str):
    db = get_db()
    doc = db.progress.find_one({"analysis_id": analysis_id}, {"_id": 0})
    return doc or {"step": "starting", "percent": 0}


def clear_progress(analysis_id: str):
    db = get_db()
    db.progress.delete_one({"analysis_id": analysis_id})


# ── Comparison ──


def get_comparison(id1: str, id2: str):
    r1 = get_results(id1)
    r2 = get_results(id2)
    a1 = get_analysis(id1)
    a2 = get_analysis(id2)
    if not r1 or not r2:
        return None
    return {
        "analysis1": a1,
        "analysis2": a2,
        "results1": r1,
        "results2": r2,
    }
