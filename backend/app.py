"""
Flask backend for Customer Review AnZlyze.
Provides REST API for dataset upload, ML analysis, results retrieval,
authentication, export, email, comparison, and re-run.
"""
import os
import re
import uuid

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
        return pd.read_csv(filepath)
    elif ext in ("xlsx", "xls"):
        return pd.read_excel(filepath)
    elif ext == "json":
        return pd.read_json(filepath)
    return pd.read_csv(filepath)


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

        text_column = request.form.get("text_column", "")
        rating_column = request.form.get("rating_column", "")

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
    """Run full ML analysis pipeline."""
    try:
        data = request.get_json() or {}
        analysis_id = data.get("analysis_id")
        text_column = data.get("text_column")
        rating_column = data.get("rating_column")
        custom_categories = data.get("custom_categories")
        use_transformer = data.get("use_transformer", False)

        if not analysis_id:
            return jsonify({"error": "analysis_id is required"}), 400

        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        update_analysis_status(analysis_id, "processing")
        set_progress(analysis_id, "Loading dataset", 5)

        filepath = os.path.join(UPLOAD_DIR, analysis.get("stored_path", ""))
        if not os.path.exists(filepath):
            update_analysis_status(analysis_id, "error")
            return jsonify({"error": "Dataset file not found on server"}), 404

        df = read_file_to_df(filepath, analysis.get("stored_path", ""))
        text_col = text_column or analysis.get("text_column") or df.columns[0]
        rating_col = rating_column or analysis.get("rating_column")

        if text_col not in df.columns:
            update_analysis_status(analysis_id, "error")
            return jsonify({"error": f"Column '{text_col}' not found. Available: {df.columns.tolist()}"}), 400

        def progress_cb(step, pct):
            set_progress(analysis_id, step, pct)

        ml_results = run_full_pipeline(df, text_col, rating_col,
                                       progress_cb=progress_cb,
                                       custom_categories=custom_categories,
                                       use_transformer=use_transformer)

        set_progress(analysis_id, "Detecting problems", 75)
        problems = detect_problems(
            ml_results["predictions"],
            ml_results["feature_names"],
            custom_categories=custom_categories,
        )

        set_progress(analysis_id, "Generating recommendations", 90)
        recommendations = generate_recommendations(
            problems["problems"],
            ml_results["sentiment_distribution"],
        )

        save_data = {
            "best_model": ml_results["best_model"],
            "best_accuracy": ml_results["best_accuracy"],
            "sentiment_distribution": ml_results["sentiment_distribution"],
            "problems": problems,
            "recommendations": recommendations,
            "model_results": ml_results["models"],
        }
        save_results(analysis_id, save_data)
        save_predictions(analysis_id, ml_results["predictions"])
        update_analysis_status(analysis_id, "completed", ml_results["sentiment_distribution"]["total"])

        set_progress(analysis_id, "Complete", 100)

        return jsonify({
            "analysis_id": analysis_id,
            "status": "completed",
            "best_model": ml_results["best_model"],
            "best_accuracy": ml_results["best_accuracy"],
            "sentiment_distribution": ml_results["sentiment_distribution"],
            "problem_count": problems["problem_count"],
            "total_recommendations": recommendations["total_recommendations"],
        })

    except Exception as e:
        if "analysis_id" in dir():
            try:
                update_analysis_status(analysis_id, "error")
                clear_progress(analysis_id)
            except Exception:
                pass
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Progress
# ──────────────────────────────────────────────
@app.route("/api/progress/<analysis_id>")
def progress(analysis_id):
    """Get analysis progress."""
    return jsonify(get_progress(analysis_id))


# ──────────────────────────────────────────────
# Get Results
# ──────────────────────────────────────────────
@app.route("/api/results/<analysis_id>")
def results(analysis_id):
    """Get analysis results."""
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        results_data = get_results(analysis_id)
        if not results_data:
            return jsonify({"error": "Results not ready yet"}), 404

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
    """Get paginated predictions with optional sentiment filter and search."""
    try:
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)
        sentiment = request.args.get("sentiment", None)
        q = request.args.get("q", None)

        data = get_predictions(analysis_id, limit, offset, sentiment, q)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch predictions: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Trend Analysis
# ──────────────────────────────────────────────
@app.route("/api/trend/<analysis_id>")
def trend_analysis(analysis_id):
    """Get sentiment distribution over time if dataset has a date column."""
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
        for col in df.columns:
            if df[col].dtype == "object":
                sample = df[col].dropna().iloc[:50] if len(df[col].dropna()) > 50 else df[col].dropna()
                if len(sample) < 3:
                    continue
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().sum() > len(sample) * 0.5:
                    date_col = col
                    break

        if not date_col:
            return jsonify({"trend": [], "message": "No date column detected"})

        dates = pd.to_datetime(df[date_col], errors="coerce")
        predictions_list = predictions_data.get("predictions", [])
        trend: dict[str, dict] = {}
        for i, pred in enumerate(predictions_list):
            if i >= len(dates) or pd.isna(dates[i]):
                continue
            date_key = dates[i].strftime("%Y-%m-%d")
            if date_key not in trend:
                trend[date_key] = {"date": date_key, "positive": 0, "negative": 0, "neutral": 0, "total": 0}
            sentiment = pred.get("sentiment", "neutral")
            trend[date_key][sentiment] += 1
            trend[date_key]["total"] += 1

        sorted_trend = sorted(trend.values(), key=lambda x: x["date"])
        return jsonify({"trend": sorted_trend, "message": None})
    except Exception as e:
        return jsonify({"error": f"Trend analysis failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Word Frequency
# ──────────────────────────────────────────────
@app.route("/api/word-frequency/<analysis_id>")
def word_frequency(analysis_id):
    """Get word frequency counts from analyzed reviews."""
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        predictions_data = get_predictions(analysis_id, limit=10000)
        predictions = predictions_data.get("predictions", [])

        from collections import Counter
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words("english"))

        word_counts: dict[str, dict] = {}
        for pred in predictions:
            text = str(pred.get("review_text", ""))
            sentiment = pred.get("sentiment", "neutral")
            cleaned = re.sub(r"[^\w\s]", "", text.lower())
            for word in cleaned.split():
                if len(word) > 2 and word not in stop_words and word.isalpha():
                    if word not in word_counts:
                        word_counts[word] = {"word": word, "total": 0, "positive": 0, "negative": 0, "neutral": 0}
                    word_counts[word]["total"] += 1
                    word_counts[word][sentiment] += 1

        sorted_words = sorted(word_counts.values(), key=lambda x: x["total"], reverse=True)[:100]
        return jsonify({"words": sorted_words})
    except Exception as e:
        return jsonify({"error": f"Word frequency failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# AI Summary
# ──────────────────────────────────────────────
@app.route("/api/summary/<analysis_id>")
def ai_summary(analysis_id):
    """Generate an executive summary using the transformer model."""
    try:
        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        results_data = get_results(analysis_id)
        if not results_data:
            return jsonify({"error": "Results not ready"}), 404

        dist = results_data.get("sentiment_distribution", {})
        total = dist.get("total", 0)
        pos = dist.get("positive", 0)
        neg = dist.get("negative", 0)
        neu = dist.get("neutral", 0)
        pos_pct = round(pos / max(total, 1) * 100, 1)
        neg_pct = round(neg / max(total, 1) * 100, 1)

        problems = results_data.get("problems", {}).get("problems", [])
        top_problems = [p["category"] for p in problems[:3]]
        top_problems_str = ", ".join(top_problems) if top_problems else "no major issues detected"

        text_to_summarize = (
            f"Customer review analysis of {total} reviews shows {pos_pct}% positive, "
            f"{neg_pct}% negative, and {round(neu / max(total, 1) * 100, 1)}% neutral sentiment. "
            f"Top issues: {top_problems_str}. "
            f"Overall customer feedback indicates {('strong satisfaction' if pos_pct > 60 else 'mixed feelings' if pos_pct > 40 else 'significant concerns')}."
        )

        set_progress(analysis_id, "Generating AI summary", 95)
        try:
            from transformers import pipeline as hf_pipeline
            summarizer = hf_pipeline("summarization", model="facebook/bart-large-cnn", device=-1)
            summary_result = summarizer(text_to_summarize, max_length=80, min_length=20, do_sample=False)
            summary_text = summary_result[0]["summary_text"]
        except Exception:
            summary_text = text_to_summarize

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

        send_report_email(to_email, analysis_id, {"analysis": analysis, "results": results_data})
        return jsonify({"status": "sent", "email": to_email})
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
        use_transformer = data.get("use_transformer", False)

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
                                       custom_categories=custom_categories,
                                       use_transformer=use_transformer)

        problems = detect_problems(ml_results["predictions"], ml_results["feature_names"],
                                   custom_categories=custom_categories)
        recommendations = generate_recommendations(problems["problems"], ml_results["sentiment_distribution"])

        save_data = {
            "best_model": ml_results["best_model"],
            "best_accuracy": ml_results["best_accuracy"],
            "sentiment_distribution": ml_results["sentiment_distribution"],
            "problems": problems,
            "recommendations": recommendations,
            "model_results": ml_results["models"],
        }
        save_results(new_id, save_data)
        save_predictions(new_id, ml_results["predictions"])
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
        })

    except Exception as e:
        return jsonify({"error": f"Re-run failed: {str(e)}"}), 500


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
