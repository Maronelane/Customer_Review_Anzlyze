"""
SQLite database for storing analysis results.
"""
import sqlite3
import json
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "anzlyze.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            stored_path TEXT,
            text_column TEXT NOT NULL,
            rating_column TEXT,
            total_reviews INTEGER,
            status TEXT DEFAULT 'uploaded',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS results (
            id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL,
            best_model TEXT,
            best_accuracy REAL,
            sentiment_distribution TEXT,
            problems TEXT,
            recommendations TEXT,
            model_results TEXT,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT NOT NULL,
            review_text TEXT,
            sentiment TEXT,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        );
    """)
    conn.commit()
    conn.close()


def create_analysis(filename: str, text_column: str, rating_column: str = None, stored_path: str = None) -> dict:
    conn = get_conn()
    analysis_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO analyses (id, filename, text_column, rating_column, stored_path, status) VALUES (?, ?, ?, ?, ?, 'uploaded')",
        (analysis_id, filename, text_column, rating_column, stored_path),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    return dict(row)


def update_analysis_status(analysis_id: str, status: str, total_reviews: int = None):
    conn = get_conn()
    if total_reviews is not None:
        conn.execute("UPDATE analyses SET status = ?, total_reviews = ?, completed_at = ? WHERE id = ?",
                      (status, total_reviews, datetime.utcnow().isoformat(), analysis_id))
    else:
        conn.execute("UPDATE analyses SET status = ? WHERE id = ?", (status, analysis_id))
    conn.commit()
    conn.close()


def save_results(analysis_id: str, data: dict):
    conn = get_conn()
    result_id = str(uuid.uuid4())[:8]
    conn.execute(
        """INSERT INTO results (id, analysis_id, best_model, best_accuracy, sentiment_distribution,
           problems, recommendations, model_results) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            result_id,
            analysis_id,
            data.get("best_model"),
            data.get("best_accuracy"),
            json.dumps(data.get("sentiment_distribution")),
            json.dumps(data.get("problems")),
            json.dumps(data.get("recommendations")),
            json.dumps(data.get("model_results")),
        ),
    )
    conn.commit()
    conn.close()
    return result_id


def save_predictions(analysis_id: str, predictions: list[dict]):
    conn = get_conn()
    for p in predictions:
        conn.execute(
            "INSERT INTO predictions (analysis_id, review_text, sentiment) VALUES (?, ?, ?)",
            (analysis_id, p["text"][:2000], p["sentiment"]),
        )
    conn.commit()
    conn.close()


def get_analysis(analysis_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_results(analysis_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM results WHERE analysis_id = ?", (analysis_id,)).fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    for field in ["sentiment_distribution", "problems", "recommendations", "model_results"]:
        if result.get(field):
            result[field] = json.loads(result[field])
    return result


def get_predictions(analysis_id: str, limit: int = 100, offset: int = 0, sentiment_filter: str = None):
    conn = get_conn()
    if sentiment_filter:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE analysis_id = ? AND sentiment = ? LIMIT ? OFFSET ?",
            (analysis_id, sentiment_filter, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE analysis_id = ? LIMIT ? OFFSET ?",
            (analysis_id, limit, offset),
        ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) as cnt FROM predictions WHERE analysis_id = ?" + (" AND sentiment = ?" if sentiment_filter else ""),
        (analysis_id, sentiment_filter) if sentiment_filter else (analysis_id,),
    ).fetchone()["cnt"]
    conn.close()
    return {"predictions": [dict(r) for r in rows], "total": total}


def list_analyses():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM analyses ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_db()
