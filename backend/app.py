"""
Flask backend for Customer Review AnZlyze.
Provides REST API for dataset upload, ML analysis, results retrieval,
authentication, export, email, comparison, and re-run.
"""
import os
import re
import uuid
import threading

import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flasgger import Swagger

from db import (
    create_analysis, update_analysis_status, save_results,
    save_predictions, get_analysis, get_results, get_predictions, list_analyses,
    init_mongo, create_user, get_user_by_username, get_user_by_id,
    set_progress, get_progress, clear_progress, get_comparison,
)
from auth import hash_password, check_password, create_tokens, token_required
from ml_engine import run_full_pipeline
from problem_detector import detect_problems
from recommender import generate_recommendations
from spam_detector import detect_spam, detect_duplicates
from clustering import cluster_reviews, get_cluster_summary
from export_service import generate_excel, generate_pdf
from email_service import send_report_email

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-anzlyze")

CORS(app, supports_credentials=True, origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
])

swagger = app.config["SWAGGER"] = {
    "title": "AnZlyze API",
    "version": "2.0.0",
    "description": "Customer Review Intelligence Platform API",
}
Swagger(app)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}
MAX_FILE_SIZE_MB = 50


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def read_file_to_df(filepath: str, filename: str) -> pd.DataFrame:
    ext = filename.rsplit(".", 1)[1].lower()
    if ext == "csv":
        df = pd.read_csv(filepath)
    elif ext in ("xlsx", "xls"):
        df = pd.read_excel(filepath)
    elif ext == "json":
        df = _read_json(filepath)
    else:
        df = pd.read_csv(filepath)

    for col in df.columns:
        df[col] = df[col].apply(lambda x: "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x))
    return df


def _read_json(filepath: str) -> pd.DataFrame:
    """Read JSON into a DataFrame, handling multiple formats."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        raise ValueError("JSON file is empty")

    # Try standard JSON first
    try:
        return pd.read_json(filepath)
    except (ValueError, TypeError):
        pass

    # Try JSON Lines (one object per line)
    try:
        return pd.read_json(filepath, lines=True)
    except (ValueError, TypeError):
        pass

    # Manual parse: handle array of objects or JSONL
    import json as _json
    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    if isinstance(data, list):
        if len(data) == 0:
            raise ValueError("JSON file contains an empty array")
        # If items are dicts, normalize; if strings, wrap in a single column
        if isinstance(data[0], dict):
            return pd.json_normalize(data)
        return pd.DataFrame({"text": data})

    if isinstance(data, dict):
        # Could be a single object or a dict of arrays
        for v in data.values():
            if isinstance(v, list) and len(v) > 0:
                return pd.DataFrame(data)
        # Single dict => wrap
        return pd.DataFrame([data])

    raise ValueError(f"Unsupported JSON structure: {type(data).__name__}")


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────
@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "Customer Review AnZlyze"})


# ──────────────────────────────────────────────
# Auth: Register
# ──────────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if get_user_by_username(username):
        return jsonify({"error": "Username already exists"}), 409

    user = create_user(username, hash_password(password))
    access, refresh = create_tokens(user["user_id"], username)
    return jsonify({
        "user_id": user["user_id"],
        "username": username,
        "access_token": access,
        "refresh_token": refresh,
    }), 201


# ──────────────────────────────────────────────
# Auth: Login
# ──────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def login():
    """Login with username and password."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = get_user_by_username(username)
    if not user or not check_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid username or password"}), 401

    access, refresh = create_tokens(user["_id"], username)
    return jsonify({
        "user_id": user["_id"],
        "username": username,
        "access_token": access,
        "refresh_token": refresh,
    })


# ──────────────────────────────────────────────
# Auth: Me
# ──────────────────────────────────────────────
@app.route("/api/me")
@token_required
def me():
    """Get current user info."""
    user = get_user_by_id(request.current_user["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


# ──────────────────────────────────────────────
# Upload Dataset
# ──────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload_dataset():
    """Upload CSV, Excel, or JSON dataset."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Supported formats: CSV, Excel (.xlsx), JSON"}), 400

        file.seek(0, os.SEEK_END)
        size_mb = file.tell() / (1024 * 1024)
        file.seek(0)
        if size_mb > MAX_FILE_SIZE_MB:
            return jsonify({"error": f"File too large (max {MAX_FILE_SIZE_MB}MB)"}), 400

        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(UPLOAD_DIR, unique_name)
        file.save(filepath)

        df = read_file_to_df(filepath, filename)
        columns = df.columns.tolist()
        preview = df.head(5).fillna("").to_dict(orient="records")
        row_count = len(df)

        # 1. Safely retrieve form parameters first
        text_column = request.form.get("text_column", "")
        rating_column = request.form.get("rating_column", "")

        # 2. Auto-detect rating column if not provided
        if not rating_column:
            for col in columns:
                col_lower = str(col).lower()
                if any(kw in col_lower for kw in ["rating", "score", "star", "rate", "overall"]):
                    rating_column = col
                    break
        user_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from auth import decode_token
                token = auth_header.split(" ", 1)[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
            except Exception:
                pass

        analysis = create_analysis(filename, text_column or columns[0], rating_column or None,
                                   stored_path=unique_name, user_id=user_id)

        return jsonify({
            "analysis_id": analysis["_id"],
            "filename": filename,
            "columns": columns,
            "row_count": row_count,
            "preview": preview,
            "stored_path": unique_name,
        }), 201

    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Run Analysis
# ──────────────────────────────────────────────
@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Start ML analysis pipeline in background thread. Returns immediately."""
    try:
        data = request.get_json() or {}
        analysis_id = data.get("analysis_id")
        text_column = data.get("text_column")
        rating_column = data.get("rating_column")
        custom_categories = data.get("custom_categories")

        if not analysis_id:
            return jsonify({"error": "analysis_id is required"}), 400

        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        filepath = os.path.join(UPLOAD_DIR, analysis.get("stored_path", ""))
        if not os.path.exists(filepath):
            return jsonify({"error": "Dataset file not found on server"}), 404

        update_analysis_status(analysis_id, "processing")
        set_progress(analysis_id, "Queued for analysis", 2)

        def _run_pipeline():
            try:
                set_progress(analysis_id, "Loading dataset", 5)
                df = read_file_to_df(filepath, analysis.get("stored_path", ""))
                text_col = text_column or analysis.get("text_column") or df.columns[0]
                rating_col = rating_column or analysis.get("rating_column")

                if text_col not in df.columns:
                    update_analysis_status(analysis_id, "error")
                    set_progress(analysis_id, "Error: column not found", 0)
                    return

                def progress_cb(step, pct):
                    set_progress(analysis_id, step, pct)

                ml_results = run_full_pipeline(df, text_col, rating_col,
                                               progress_cb=progress_cb,
                                               custom_categories=custom_categories)

                set_progress(analysis_id, "Detecting spam & fake reviews", 65)
                detect_spam(ml_results["predictions"])
                detect_duplicates(ml_results["predictions"])

                spam_count = sum(1 for p in ml_results["predictions"] if p.get("is_flagged"))
                total = len(ml_results["predictions"])

                set_progress(analysis_id, "Clustering root causes", 70)
                try:
                    cluster_reviews(ml_results["predictions"])
                    cluster_summary = get_cluster_summary(ml_results["predictions"])
                except Exception:
                    cluster_summary = []

                set_progress(analysis_id, "Detecting problems", 75)
                problems = detect_problems(
                    ml_results["predictions"],
                    ml_results["feature_names"],
                    custom_categories=custom_categories,
                )

                set_progress(analysis_id, "Generating data-driven recommendations", 90)
                recommendations = generate_recommendations(
                    problems=problems.get("problems", []),
                    sentiment_distribution=ml_results["sentiment_distribution"],
                    top_complaint_words=problems.get("top_complaint_words", []),
                    negative_review_sample=problems.get("negative_review_sample", []),
                )

                spam_summary = {
                    "total_flagged": spam_count,
                    "total_reviews": total,
                    "flagged_percentage": round(spam_count / max(total, 1) * 100, 2),
                }

                # Build per-model full results
                model_runs = {}
                all_preds = ml_results.get("all_model_predictions", {})
                all_dists = ml_results.get("all_model_distributions", {})
                for m_name, m_preds in all_preds.items():
                    m_dist = all_dists.get(m_name, ml_results["sentiment_distribution"])
                    detect_spam(m_preds)
                    detect_duplicates(m_preds)
                    m_spam_count = sum(1 for p in m_preds if p.get("is_flagged"))
                    m_total = len(m_preds)
                    try:
                        cluster_reviews(m_preds)
                        m_cluster_summary = get_cluster_summary(m_preds)
                    except Exception:
                        m_cluster_summary = []
                    m_problems = detect_problems(m_preds, ml_results["feature_names"], custom_categories=custom_categories)
                    m_recommendations = generate_recommendations(
                        problems=m_problems.get("problems", []),
                        sentiment_distribution=m_dist,
                        top_complaint_words=m_problems.get("top_complaint_words", []),
                        negative_review_sample=m_problems.get("negative_review_sample", []),
                    )
                    model_runs[m_name] = {
                        "sentiment_distribution": m_dist,
                        "problems": m_problems,
                        "recommendations": m_recommendations,
                        "spam_summary": {
                            "total_flagged": m_spam_count,
                            "total_reviews": m_total,
                            "flagged_percentage": round(m_spam_count / max(m_total, 1) * 100, 2),
                        },
                        "cluster_summary": m_cluster_summary,
                        "predictions": m_preds,
                    }

                save_data = {
                    "best_model": ml_results["best_model"],
                    "best_accuracy": ml_results["best_accuracy"],
                    "sentiment_distribution": ml_results["sentiment_distribution"],
                    "problems": problems,
                    "recommendations": recommendations,
                    "model_results": ml_results["models"],
                    "spam_summary": spam_summary,
                    "cluster_summary": cluster_summary,
                    "model_runs": {k: {kk: vv for kk, vv in v.items() if kk != "predictions"} for k, v in model_runs.items()},
                }
                save_results(analysis_id, save_data)
                save_predictions(analysis_id, ml_results["predictions"])
                for m_name, m_data in model_runs.items():
                    save_predictions(analysis_id, m_data["predictions"], model=m_name)
                update_analysis_status(analysis_id, "completed", ml_results["sentiment_distribution"]["total"])

                set_progress(analysis_id, "Complete", 100)

            except Exception as e:
                try:
                    update_analysis_status(analysis_id, "error")
                    set_progress(analysis_id, f"Error: {str(e)[:100]}", 0)
                except Exception:
                    pass

        thread = threading.Thread(target=_run_pipeline, daemon=True)
        thread.start()

        return jsonify({
            "analysis_id": analysis_id,
            "status": "processing",
        }), 202

    except Exception as e:
        return jsonify({"error": f"Failed to start analysis: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Progress
# ──────────────────────────────────────────────
@app.route("/api/progress/<analysis_id>")
def progress(analysis_id):
    """Get analysis progress."""
    prog = get_progress(analysis_id)
    analysis = get_analysis(analysis_id)
    if analysis:
        prog["status"] = analysis.get("status", "processing")
    return jsonify(prog)


# ──────────────────────────────────────────────
# Get Results
# ──────────────────────────────────────────────
@app.route("/api/results/<analysis_id>")
def results(analysis_id):
    """Get analysis results. Optional ?model= param to switch active model."""
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        results_data = get_results(analysis_id)
        if not results_data:
            return jsonify({"error": "Results not ready yet"}), 404

        model = request.args.get("model")
        model_runs = results_data.get("model_runs", {})

        if model and model in model_runs:
            run = model_runs[model]
            results_data = {**results_data, **run}
            results_data["active_model"] = model
        else:
            results_data["active_model"] = results_data.get("best_model", "")

        return jsonify({
            "analysis": analysis,
            "results": results_data,
        })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch results: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Get Predictions (paginated, with search)
# ──────────────────────────────────────────────
@app.route("/api/predictions/<analysis_id>")
def predictions(analysis_id):
    """Get paginated predictions with optional sentiment filter, search, and model."""
    try:
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)
        sentiment = request.args.get("sentiment", None)
        q = request.args.get("q", None)
        model = request.args.get("model", None)

        data = get_predictions(analysis_id, limit, offset, sentiment, q, model=model)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch predictions: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Trend Analysis (Sentiment by Month)
# ──────────────────────────────────────────────
@app.route("/api/trend/<analysis_id>")
def trend_analysis(analysis_id):
    """Get sentiment distribution aggregated by month if dataset has a date column."""
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        predictions_data = get_predictions(analysis_id, limit=10000)
        filepath = os.path.join(UPLOAD_DIR, analysis.get("stored_path", ""))
        if not os.path.exists(filepath):
            return jsonify({"error": "Dataset file not found"}), 404

        df = read_file_to_df(filepath, analysis.get("stored_path", ""))
        date_col = None

        # Robust date column detection
        for col in df.columns:
            dtype = str(df[col].dtype)
            if "datetime" in dtype:
                date_col = col
                break
            
            sample = df[col].dropna()
            if len(sample) < 3:
                continue
            
            col_lower = str(col).lower()
            name_hint = any(h in col_lower for h in ["date", "time", "day", "created", "timestamp", "year"])
            
            try:
                parsed = pd.to_datetime(sample.astype(str).head(20), errors="coerce", format="mixed")
            except TypeError:
                parsed = pd.to_datetime(sample.astype(str).head(20), errors="coerce")
                
            valid_ratio = parsed.notna().sum() / len(sample.head(20))
            if valid_ratio > 0.4 or (name_hint and valid_ratio > 0.1):
                date_col = col
                break

        if not date_col:
            return jsonify({"trend": [], "message": "No date column detected"})

        try:
            valid_dates = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
        except TypeError:
            valid_dates = pd.to_datetime(df[date_col], errors="coerce")

        predictions_list = predictions_data.get("predictions", [])

        trend: dict[str, dict] = {}
        for i, pred in enumerate(predictions_list):
            if i >= len(valid_dates):
                break
            dt_val = valid_dates.iloc[i]
            if pd.isna(dt_val):
                continue
            
            # Group by Year-Month format (e.g., "2014-05") to smooth out daily spikes
            date_key = dt_val.strftime("%Y-%m")
            if date_key.startswith("1970"):
                continue

            if date_key not in trend:
                trend[date_key] = {"date": date_key, "positive": 0, "negative": 0, "neutral": 0, "total": 0}
            
            sentiment = pred.get("sentiment", "neutral")
            if sentiment in trend[date_key]:
                trend[date_key][sentiment] += 1
                trend[date_key]["total"] += 1

        sorted_trend = sorted(trend.values(), key=lambda x: x["date"])
        
        if not sorted_trend:
            return jsonify({"trend": [], "message": "No valid monthly date entries found"})
            
        return jsonify({"trend": sorted_trend, "message": None})
    except Exception as e:
        return jsonify({"error": f"Monthly trend analysis failed: {str(e)}"}), 500
# ──────────────────────────────────────────────
# Word Frequency
# ──────────────────────────────────────────────
@app.route("/api/word-frequency/<analysis_id>")
def word_frequency(analysis_id):
    """Get word frequency counts from analyzed reviews with high accuracy.

    Improvements over the naive implementation:
      * Keeps meaningful review words (good, great, bad, battery...) instead of
        wrongly treating them as stopwords.
      * Merges word forms via lemmatization / form mapping (sound/sounds/sound,
        work/working/worked -> work).
      * Attributes each word to a sentiment using its OWN sentence (with
        negation flipping), not the whole review, so the positive/negative tabs
        are realistic instead of diluted.
      * Excludes spam and drops noisy bigrams so the cloud shows real themes.
    """
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        model = request.args.get("model", None)
        predictions_data = get_predictions(analysis_id, limit=10000, model=model)
        predictions = predictions_data.get("predictions", [])

        from nltk.corpus import stopwords
        from nltk.stem import WordNetLemmatizer
        from nltk.tokenize import sent_tokenize
        from ml_engine import LEMMATIZER

        # Feature-relevant words that should NEVER be dropped just because they
        # are common English filler. These carry real meaning in review analysis.
        _MEANINGFUL = {
            "good", "great", "bad", "well", "better", "best", "worst", "nice",
            "excellent", "amazing", "awesome", "superb", "poor", "terrible",
            "battery", "sound", "quality", "price", "product", "works", "work",
            "camera", "display", "screen", "fast", "slow", "comfortable",
        }
        stop_words = set(stopwords.words("english")) - _MEANINGFUL
        stop_words |= {
            "this", "that", "with", "from", "have", "been", "were", "they",
            "their", "would", "could", "should", "about", "also", "just",
            "only", "very", "much", "more", "than", "some", "into", "made",
            "make", "thing", "things", "one", "two", "get", "got", "back",
            "even", "still", "after", "before", "being", "over", "such",
            "through", "first", "last", "long", "little", "own", "other",
            "old", "right", "big", "high", "small", "large", "next", "early",
            "young", "important", "same", "able", "every", "found", "look",
            "day", "would", "really", "the", "and", "for", "are", "was",
        }
        stop_words.discard("not")
        stop_words.discard("no")

        # Compact polarity lexicon for sentence-level sentiment attribution.
        _POS = set("""good great nice excellent amazing awesome superb fantastic
            wonderful perfect love loved loves best better awesome cool outstanding
            brilliant great comfortable fast smooth crisp clear sharp bright easy
            happy satisfied impressive premium solid robust stunning super quality
            value useful helpful durable reliable powerful responsive""".split())
        _NEG = set("""bad poor terrible worst awful horrible disappointing
            disappointed useless broken waste cheap flimsy slow stuck lag issue
            problem problems complaint complain defective faulty dead fail failed
            fails not_work not_works not_working dont_work dont_works heavy noise
            noisy crack scratched scratch stop stopped stopping hate waste worst""".split())
        _NEG_WORDS = {"not", "no", "never", "dont", "doesnt", "didnt", "cant",
                      "wont", "wasnt", "isnt", "arent", "hardly", "barely"}

        # Merge common inflected verb/word forms to a single base so review
        # themes aren't fragmented (work/working/worked/works -> work). The
        # default noun lemmatizer misses verb forms, so we map the frequent ones.
        _WORD_BASE = {
            "works": "work", "worked": "work", "working": "work",
            "using": "use", "used": "use",
            "buying": "buy", "bought": "buy",
            "charging": "charge", "charged": "charge",
            "connecting": "connect", "connected": "connect",
            "disconnecting": "disconnect", "disconnected": "disconnect",
            "pairing": "pair", "paired": "pair",
            "loved": "love",
            "feeling": "feel",
            "improved": "improve", "improving": "improve",
            "expected": "expect",
        }

        def _base_word(word):
            return _WORD_BASE.get(word, word)

        word_counts: dict[str, dict] = {}

        for pred in predictions:
            # Exclude spam so junk/flags don't distort the cloud.
            if pred.get("is_flagged"):
                continue
            text = str(pred.get("review_text", ""))
            if not text.strip():
                continue

            for sentence in sent_tokenize(text) or [text]:
                raw = re.sub(r"[^\w\s]", " ", sentence.lower())
                tokens = [t for t in raw.split() if len(t) > 2 and t.isalpha()]
                if not tokens:
                    continue

                # 1. Clean + lemmatize, remembering whether each token is
                #    locally negated (the 2 tokens after a negation word).
                scoped = []
                pending_neg = 0
                for t in tokens:
                    if t in _NEG_WORDS:
                        pending_neg = 2
                        continue
                    if pending_neg > 0:
                        scoped.append(("not_" + LEMMATIZER.lemmatize(t)) if t not in stop_words else None)
                        pending_neg -= 1
                    else:
                        scoped.append(LEMMATIZER.lemmatize(t) if t not in stop_words else None)

                # 2. Local sentence sentiment (negation-aware).
                pos = neg = 0
                for w in scoped:
                    if not w:
                        continue
                    negated = w.startswith("not_")
                    base = w[4:] if negated else w
                    if base in _POS:
                        if negated:
                            neg += 1
                        else:
                            pos += 1
                    elif base in _NEG:
                        if negated:
                            pos += 1
                        else:
                            neg += 1
                sent = "positive" if pos > neg else ("negative" if neg > pos else "neutral")

                # 3. Count each clean word under that local sentiment.
                for w in scoped:
                    if not w or len(w) < 3:
                        continue
                    word = _base_word(w[4:] if w.startswith("not_") else w)
                    if word in stop_words:
                        continue
                    entry = word_counts.get(word) or {
                        "word": word, "total": 0, "positive": 0, "negative": 0, "neutral": 0,
                    }
                    entry["total"] += 1
                    entry[sent] += 1
                    word_counts[word] = entry

        sorted_words = sorted(word_counts.values(), key=lambda x: x["total"], reverse=True)[:120]
        return jsonify({"words": sorted_words})
    except Exception as e:
        return jsonify({"error": f"Word frequency failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# AI Summary
# ──────────────────────────────────────────────
@app.route("/api/summary/<analysis_id>")
def ai_summary(analysis_id):
    """Generate a rich executive summary from analysis results."""
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        results_data = get_results(analysis_id)
        if not results_data:
            return jsonify({"error": "Results not ready"}), 404

        model = request.args.get("model", None)
        model_runs = results_data.get("model_runs", {})
        if model and model in model_runs:
            run = model_runs[model]
            dist = run.get("sentiment_distribution", results_data.get("sentiment_distribution", {}))
            problems = run.get("problems", results_data.get("problems", {}))
            recommendations_data = run.get("recommendations", results_data.get("recommendations", {}))
            spam_summary = run.get("spam_summary", results_data.get("spam_summary", {}))
            cluster_summary = run.get("cluster_summary", results_data.get("cluster_summary", []))
        else:
            dist = results_data.get("sentiment_distribution", {})
            problems = results_data.get("problems", {})
            recommendations_data = results_data.get("recommendations", {})
            spam_summary = results_data.get("spam_summary", {})
            cluster_summary = results_data.get("cluster_summary", [])

        total = dist.get("total", 0)
        pos = dist.get("positive", 0)
        neg = dist.get("negative", 0)
        neu = dist.get("neutral", 0)
        pos_pct = round(pos / max(total, 1) * 100, 1)
        neg_pct = round(neg / max(total, 1) * 100, 1)
        neu_pct = round(neu / max(total, 1) * 100, 1)

        problems_list = problems.get("problems", [])
        top_complaint_words = problems.get("top_complaint_words", [])
        recommendations = recommendations_data.get("recommendations", [])

        top_problems = [p["category"].replace("_", " ").title() for p in problems_list[:3]]
        top_problem_detail = []
        for p in problems_list[:3]:
            top_problem_detail.append(
                f"  - {p['category'].replace('_', ' ').title()}: "
                f"{p['frequency']} mentions ({p['percentage']}% of negative reviews, severity: {p['severity']})"
            )
        top_problems_str = ", ".join(top_problems) if top_problems else "no major issues detected"

        critical_count = sum(1 for r in recommendations if r.get("priority") == "critical")
        high_count = sum(1 for r in recommendations if r.get("priority") == "high")

        spam_flagged = spam_summary.get("total_flagged", 0)
        spam_pct = spam_summary.get("flagged_percentage", 0)

        cluster_count = len(cluster_summary)
        high_clusters = sum(1 for c in cluster_summary if c.get("severity") == "high")

        top_words_str = ", ".join([w["word"] for w in top_complaint_words[:8]]) if top_complaint_words else "none"

        lines = ["Executive Review & Strategic Action Summary", ""]

        lines.append(
            f"Overview: Analyzed {total:,} customer reviews. "
            f"Sentiment breakdown: {pos_pct}% positive ({pos}), "
            f"{neg_pct}% negative ({neg}), {neu_pct}% neutral ({neu})."
        )

        if pos_pct > 60:
            lines.append(f"Overall customer feedback indicates strong satisfaction ({pos_pct}% positive).")
        elif pos_pct > 40:
            lines.append(f"Customer sentiment is mixed — {pos_pct}% positive but {neg_pct}% negative.")
        else:
            lines.append(f"Significant concerns: only {pos_pct}% positive sentiment with {neg_pct}% negative.")

        lines.append("")
        lines.append("Key Findings:")
        if top_problems:
            lines.append(f"Top issues identified: {top_problems_str}.")
            lines.extend(top_problem_detail)
        else:
            lines.append("No significant problem categories detected in negative reviews.")

        if critical_count > 0 or high_count > 0:
            lines.append(
                f"Priority actions: {critical_count} critical and {high_count} high-priority "
                f"recommendations require immediate attention."
            )

        if spam_flagged > 0:
            lines.append(
                f"Data quality: {spam_flagged} reviews ({spam_pct}%) flagged as potentially "
                f"fake or spam. Consider excluding these from official reports."
            )

        if cluster_count > 0:
            lines.append(
                f"Root cause analysis identified {cluster_count} distinct complaint clusters"
                f"{f', with {high_clusters} high-severity groups' if high_clusters else ''}."
            )

        if top_complaint_words:
            lines.append(f"Most frequent complaint terms: {top_words_str}.")

        lines.append("")
        lines.append("Recommended Next Steps:")
        if critical_count > 0:
            lines.append("1. Address critical-priority issues immediately to prevent further negative sentiment.")
        if high_count > 0:
            lines.append(f"{'2' if critical_count > 0 else '1'}. Tackle {high_count} high-priority areas within the next sprint.")
        if spam_pct > 10:
            step_num = 1 if critical_count + high_count == 0 else (3 if critical_count > 0 and high_count > 0 else 2)
            lines.append(f"{step_num}. Investigate and filter {spam_flagged} suspicious reviews to improve data accuracy.")
        if cluster_count > 0:
            lines.append("Review root cause clusters to understand underlying systemic issues beyond individual complaints.")
        if not recommendations:
            lines.append("Continue monitoring reviews over time to track sentiment trends.")

        summary_text = "\n".join(lines)

        set_progress(analysis_id, "Generating AI summary", 95)

        return jsonify({"summary": summary_text})
    except Exception as e:
        return jsonify({"error": f"Summary generation failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# List Analyses
# ──────────────────────────────────────────────
@app.route("/api/analyses")
def analyses():
    """List all analyses."""
    try:
        return jsonify(list_analyses())
    except Exception as e:
        return jsonify({"error": f"Failed to list analyses: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Export (PDF/Excel)
# ──────────────────────────────────────────────
@app.route("/api/export/<analysis_id>")
def export_analysis(analysis_id):
    """Export analysis as PDF or Excel."""
    try:
        fmt = request.args.get("format", "excel").lower()
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404
        results_data = get_results(analysis_id)
        if not results_data:
            return jsonify({"error": "Results not ready yet"}), 404

        export_data = {"analysis": analysis, "results": results_data}

        if fmt == "pdf":
            pdf_bytes = generate_pdf(export_data)
            return pdf_bytes, 200, {
                "Content-Type": "application/pdf",
                "Content-Disposition": f'attachment; filename="anzlyze_{analysis_id}.pdf"',
            }
        else:
            xlsx_bytes = generate_excel(export_data)
            return xlsx_bytes, 200, {
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Content-Disposition": f'attachment; filename="anzlyze_{analysis_id}.xlsx"',
            }
    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Email Report
# ──────────────────────────────────────────────
@app.route("/api/email-report", methods=["POST"])
def email_report():
    """Send analysis report via email."""
    try:
        data = request.get_json() or {}
        to_email = data.get("email")
        analysis_id = data.get("analysis_id")

        if not to_email or not analysis_id:
            return jsonify({"error": "email and analysis_id are required"}), 400

        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404
        results_data = get_results(analysis_id)
        if not results_data:
            return jsonify({"error": "Results not ready yet"}), 404

        formats = data.get("formats", ["pdf"])
        if isinstance(formats, str):
            formats = [formats]
        allowed = {"pdf", "excel"}
        formats = [f for f in formats if f in allowed] or ["pdf"]

        send_report_email(to_email, analysis_id, {"analysis": analysis, "results": results_data}, formats=tuple(formats))
        return jsonify({"status": "sent", "email": to_email, "formats": formats})
    except Exception as e:
        return jsonify({"error": f"Email failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Compare Datasets
# ──────────────────────────────────────────────
@app.route("/api/compare", methods=["POST"])
def compare():
    """Compare two analysis results side by side."""
    try:
        data = request.get_json() or {}
        id1 = data.get("analysis_id_1")
        id2 = data.get("analysis_id_2")

        if not id1 or not id2:
            return jsonify({"error": "Both analysis_id_1 and analysis_id_2 are required"}), 400

        result = get_comparison(id1, id2)
        if not result:
            return jsonify({"error": "One or both analyses not found or have no results"}), 404

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Comparison failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Re-run Analysis
# ──────────────────────────────────────────────
@app.route("/api/rerun", methods=["POST"])
def rerun():
    """Re-run analysis with same or different settings."""
    try:
        data = request.get_json() or {}
        original_id = data.get("analysis_id")
        text_column = data.get("text_column")
        rating_column = data.get("rating_column")
        custom_categories = data.get("custom_categories")

        if not original_id:
            return jsonify({"error": "analysis_id is required"}), 400

        original = get_analysis(original_id)
        if not original:
            return jsonify({"error": "Original analysis not found"}), 404

        new_analysis = create_analysis(
            original["filename"],
            text_column or original["text_column"],
            rating_column or original.get("rating_column"),
            stored_path=original.get("stored_path"),
        )
        new_id = new_analysis["_id"]

        update_analysis_status(new_id, "processing")
        set_progress(new_id, "Starting re-analysis", 5)

        filepath = os.path.join(UPLOAD_DIR, original.get("stored_path", ""))
        if not os.path.exists(filepath):
            update_analysis_status(new_id, "error")
            return jsonify({"error": "Dataset file not found"}), 404

        df = read_file_to_df(filepath, original.get("stored_path", ""))
        text_col = text_column or original.get("text_column") or df.columns[0]
        rating_col = rating_column or original.get("rating_column")

        if text_col not in df.columns:
            update_analysis_status(new_id, "error")
            return jsonify({"error": f"Column '{text_col}' not found"}), 400

        def progress_cb(step, pct):
            set_progress(new_id, step, pct)

        ml_results = run_full_pipeline(df, text_col, rating_col,
                                       progress_cb=progress_cb,
                                       custom_categories=custom_categories)

        detect_spam(ml_results["predictions"])
        detect_duplicates(ml_results["predictions"])
        spam_count = sum(1 for p in ml_results["predictions"] if p.get("is_flagged"))

        try:
            cluster_reviews(ml_results["predictions"])
            cluster_summary = get_cluster_summary(ml_results["predictions"])
        except Exception:
            cluster_summary = []

        problems = detect_problems(ml_results["predictions"], ml_results["feature_names"],
                                   custom_categories=custom_categories)

        recommendations = generate_recommendations(
            problems=problems.get("problems", []),
            sentiment_distribution=ml_results["sentiment_distribution"],
            top_complaint_words=problems.get("top_complaint_words", []),
            negative_review_sample=problems.get("negative_review_sample", []),
        )

        spam_summary = {
            "total_flagged": spam_count,
            "total_reviews": len(ml_results["predictions"]),
            "flagged_percentage": round(spam_count / max(len(ml_results["predictions"]), 1) * 100, 2),
        }

        model_runs = {}
        all_preds = ml_results.get("all_model_predictions", {})
        all_dists = ml_results.get("all_model_distributions", {})
        for m_name, m_preds in all_preds.items():
            m_dist = all_dists.get(m_name, ml_results["sentiment_distribution"])
            detect_spam(m_preds)
            detect_duplicates(m_preds)
            m_spam_count = sum(1 for p in m_preds if p.get("is_flagged"))
            m_total = len(m_preds)
            try:
                cluster_reviews(m_preds)
                m_cluster_summary = get_cluster_summary(m_preds)
            except Exception:
                m_cluster_summary = []
            m_problems = detect_problems(m_preds, ml_results["feature_names"], custom_categories=custom_categories)
            m_recommendations = generate_recommendations(
                problems=m_problems.get("problems", []),
                sentiment_distribution=m_dist,
                top_complaint_words=m_problems.get("top_complaint_words", []),
                negative_review_sample=m_problems.get("negative_review_sample", []),
            )
            model_runs[m_name] = {
                "sentiment_distribution": m_dist,
                "problems": m_problems,
                "recommendations": m_recommendations,
                "spam_summary": {
                    "total_flagged": m_spam_count,
                    "total_reviews": m_total,
                    "flagged_percentage": round(m_spam_count / max(m_total, 1) * 100, 2),
                },
                "cluster_summary": m_cluster_summary,
                "predictions": m_preds,
            }

        save_data = {
            "best_model": ml_results["best_model"],
            "best_accuracy": ml_results["best_accuracy"],
            "sentiment_distribution": ml_results["sentiment_distribution"],
            "problems": problems,
            "recommendations": recommendations,
            "model_results": ml_results["models"],
            "spam_summary": spam_summary,
            "cluster_summary": cluster_summary,
            "model_runs": {k: {kk: vv for kk, vv in v.items() if kk != "predictions"} for k, v in model_runs.items()},
        }
        save_results(new_id, save_data)
        save_predictions(new_id, ml_results["predictions"])
        for m_name, m_data in model_runs.items():
            save_predictions(new_id, m_data["predictions"], model=m_name)
        update_analysis_status(new_id, "completed", ml_results["sentiment_distribution"]["total"])
        clear_progress(new_id)

        return jsonify({
            "analysis_id": new_id,
            "status": "completed",
            "best_model": ml_results["best_model"],
            "best_accuracy": ml_results["best_accuracy"],
            "sentiment_distribution": ml_results["sentiment_distribution"],
            "problem_count": problems["problem_count"],
            "total_recommendations": recommendations["total_recommendations"],
            "spam_count": spam_count,
            "cluster_count": len(cluster_summary),
        })

    except Exception as e:
        return jsonify({"error": f"Re-run failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Spam Detection Endpoint
# ──────────────────────────────────────────────
@app.route("/api/spam/<analysis_id>")
def spam_summary(analysis_id):
    """Get spam detection summary for an analysis."""
    try:
        model = request.args.get("model", None)
        results_data = get_results(analysis_id)
        if not results_data:
            return jsonify({"error": "Results not found"}), 404

        model_runs = results_data.get("model_runs", {})
        if model and model in model_runs:
            spam_summary = model_runs[model].get("spam_summary", {})
        else:
            spam_summary = results_data.get("spam_summary", {})

        flagged = get_predictions(analysis_id, limit=10000, model=model)
        flagged_preds = flagged.get("predictions", []) if isinstance(flagged, dict) else []

        flagged_reviews = [p for p in flagged_preds if p.get("is_flagged")]
        clean_reviews = [p for p in flagged_preds if not p.get("is_flagged")]

        return jsonify({
            "spam_summary": spam_summary,
            "flagged_reviews": flagged_reviews[:50],
            "clean_count": len(clean_reviews),
        })
    except Exception as e:
        return jsonify({"error": f"Spam summary failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Root Cause Clustering Endpoint
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# Serve Built Frontend (SPA Fallback)
# ──────────────────────────────────────────────
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path.startswith("api/"):
        return jsonify({"error": "API route not found"}), 404
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index):
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({"status": "Customer Review AnZlyze API is running"})


if __name__ == "__main__":
    init_mongo()
    app.run(debug=True, port=5001)