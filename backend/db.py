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
        "spam_summary": _safe_for_mongo(data.get("spam_summary")),
        "cluster_summary": _safe_for_mongo(data.get("cluster_summary")),
    }
    db.results.insert_one(doc)


def save_predictions(analysis_id: str, predictions: list[dict], model: str = "best"):
    db = get_db()
    docs = [
        {
            "analysis_id": analysis_id,
            "model": model,
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


def get_predictions(analysis_id: str, limit: int = 100, offset: int = 0, sentiment_filter: str = None, search_query: str = None, model: str = None):
    db = get_db()
    query = {"analysis_id": analysis_id}
    if sentiment_filter:
        query["sentiment"] = sentiment_filter
    if search_query:
        query["review_text"] = {"$regex": search_query, "$options": "i"}

    if model:
        model_query = {**query, "model": model}
        total = db.predictions.count_documents(model_query)
        if total > 0:
            rows = list(db.predictions.find(model_query, {"_id": 0}).sort("_id", 1).skip(offset).limit(limit))
            return {"predictions": rows, "total": total}
        # Fall back to old predictions without model field
        fallback_query = {**query, "$or": [{"model": {"$exists": False}}, {"model": "best"}]}
        total = db.predictions.count_documents(fallback_query)
        rows = list(db.predictions.find(fallback_query, {"_id": 0}).sort("_id", 1).skip(offset).limit(limit))
        return {"predictions": rows, "total": total}

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


def _pct(val, total):
    return round(val / max(total, 1) * 100, 1)


def get_comparison(id1: str, id2: str):
    r1 = get_results(id1)
    r2 = get_results(id2)
    a1 = get_analysis(id1)
    a2 = get_analysis(id2)
    if not r1 or not r2:
        return None

    d1 = r1.get("sentiment_distribution", {})
    d2 = r2.get("sentiment_distribution", {})

    t1 = d1.get("total", 0)
    t2 = d2.get("total", 0)

    pos1 = _pct(d1.get("positive", 0), t1)
    neg1 = _pct(d1.get("negative", 0), t1)
    neu1 = _pct(d1.get("neutral", 0), t1)
    pos2 = _pct(d2.get("positive", 0), t2)
    neg2 = _pct(d2.get("negative", 0), t2)
    neu2 = _pct(d2.get("neutral", 0), t2)

    probs1 = r1.get("problems", {}).get("problems", [])
    probs2 = r2.get("problems", {}).get("problems", [])

    cats1 = {p.get("category_key") for p in probs1}
    cats2 = {p.get("category_key") for p in probs2}
    shared_problems = sorted(cats1 & cats2)
    only_in_1 = sorted(cats1 - cats2)
    only_in_2 = sorted(cats2 - cats1)

    words1 = r1.get("problems", {}).get("top_complaint_words", [])
    words2 = r2.get("problems", {}).get("top_complaint_words", [])
    word_set1 = {w["word"] for w in words1}
    word_set2 = {w["word"] for w in words2}
    shared_words = sorted(word_set1 & word_set2)
    only_words1 = sorted(word_set1 - word_set2)
    only_words2 = sorted(word_set2 - word_set1)

    spam1 = r1.get("spam_summary", {})
    spam2 = r2.get("spam_summary", {})

    acc1 = r1.get("best_accuracy", 0) or 0
    acc2 = r2.get("best_accuracy", 0) or 0

    summary_deltas = [
        {"label": "Total Reviews", "value1": t1, "value2": t2, "diff": t2 - t1, "type": "count"},
        {"label": "Positive %", "value1": pos1, "value2": pos2, "diff": round(pos2 - pos1, 1), "type": "pct",
         "better": "higher"},
        {"label": "Negative %", "value1": neg1, "value2": neg2, "diff": round(neg2 - neg1, 1), "type": "pct",
         "better": "lower"},
        {"label": "Spam Rate %", "value1": spam1.get("flagged_percentage", 0),
         "value2": spam2.get("flagged_percentage", 0),
         "diff": round((spam2.get("flagged_percentage", 0) or 0) - (spam1.get("flagged_percentage", 0) or 0), 1),
         "type": "pct", "better": "lower"},
        {"label": "Model Accuracy", "value1": round(acc1 * 100, 1), "value2": round(acc2 * 100, 1),
         "diff": round((acc2 - acc1) * 100, 1), "type": "pct", "better": "higher"},
    ]

    return {
        "analysis1": a1,
        "analysis2": a2,
        "results1": r1,
        "results2": r2,
        "deltas": {
            "sentiment": {
                "dataset1": {"positive": pos1, "negative": neg1, "neutral": neu1},
                "dataset2": {"positive": pos2, "negative": neg2, "neutral": neu2},
            },
            "problems": {
                "shared": shared_problems,
                "only_in_dataset1": only_in_1,
                "only_in_dataset2": only_in_2,
            },
            "complaint_words": {
                "shared": shared_words,
                "only_in_dataset1": only_words1,
                "only_in_dataset2": only_words2,
            },
            "spam": {
                "dataset1_rate": spam1.get("flagged_percentage", 0),
                "dataset2_rate": spam2.get("flagged_percentage", 0),
                "dataset1_flagged": spam1.get("total_flagged", 0),
                "dataset2_flagged": spam2.get("total_flagged", 0),
            },
            "models": {
                "dataset1_name": r1.get("best_model", ""),
                "dataset1_accuracy": round(acc1 * 100, 1),
                "dataset2_name": r2.get("best_model", ""),
                "dataset2_accuracy": round(acc2 * 100, 1),
            },
            "summary": summary_deltas,
        },
    }
