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


def create_analysis(filename: str, text_column: str, rating_column: str = None, stored_path: str = None) -> dict:
    db = get_db()
    analysis_id = str(uuid.uuid4())[:8]
    doc = {
        "_id": analysis_id,
        "filename": filename,
        "text_column": text_column,
        "rating_column": rating_column,
        "stored_path": stored_path,
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
        "sentiment_distribution": data.get("sentiment_distribution"),
        "problems": data.get("problems"),
        "recommendations": data.get("recommendations"),
        "model_results": data.get("model_results"),
    }
    db.results.insert_one(doc)


def save_predictions(analysis_id: str, predictions: list[dict]):
    db = get_db()
    docs = [
        {"analysis_id": analysis_id, "review_text": p["text"][:2000], "sentiment": p["sentiment"]}
        for p in predictions
    ]
    if docs:
        db.predictions.insert_many(docs)


def get_analysis(analysis_id: str):
    db = get_db()
    return db.analyses.find_one({"_id": analysis_id})


def get_results(analysis_id: str):
    db = get_db()
    doc = db.results.find_one({"analysis_id": analysis_id})
    return doc


def get_predictions(analysis_id: str, limit: int = 100, offset: int = 0, sentiment_filter: str = None):
    db = get_db()
    query = {"analysis_id": analysis_id}
    if sentiment_filter:
        query["sentiment"] = sentiment_filter
    total = db.predictions.count_documents(query)
    rows = list(db.predictions.find(query, {"_id": 0}).sort("_id", 1).skip(offset).limit(limit))
    return {"predictions": rows, "total": total}


def list_analyses():
    db = get_db()
    return list(db.analyses.find().sort("created_at", -1))
