"""
Flask backend for Customer Review AnZlyze.
Provides REST API for dataset upload, ML analysis, and results retrieval.
"""
import os
import uuid

import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from db import (
    create_analysis, update_analysis_status, save_results,
    save_predictions, get_analysis, get_results, get_predictions, list_analyses,
    init_mongo,
)
from ml_engine import run_full_pipeline
from problem_detector import detect_problems
from recommender import generate_recommendations

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-anzlyze")

CORS(app, supports_credentials=True, origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"csv"}
MAX_FILE_SIZE_MB = 50


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "Customer Review AnZlyze"})


# ──────────────────────────────────────────────
# Upload Dataset
# ──────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload_dataset():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Only CSV files are supported"}), 400

        file.seek(0, os.SEEK_END)
        size_mb = file.tell() / (1024 * 1024)
        file.seek(0)
        if size_mb > MAX_FILE_SIZE_MB:
            return jsonify({"error": f"File too large (max {MAX_FILE_SIZE_MB}MB)"}), 400

        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(UPLOAD_DIR, unique_name)
        file.save(filepath)

        df = pd.read_csv(filepath)
        columns = df.columns.tolist()
        preview = df.head(5).fillna("").to_dict(orient="records")
        row_count = len(df)

        text_column = request.form.get("text_column", "")
        rating_column = request.form.get("rating_column", "")

        analysis = create_analysis(filename, text_column or columns[0], rating_column or None, stored_path=unique_name)

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
    try:
        data = request.get_json() or {}
        analysis_id = data.get("analysis_id")
        text_column = data.get("text_column")
        rating_column = data.get("rating_column")

        if not analysis_id:
            return jsonify({"error": "analysis_id is required"}), 400

        analysis = get_analysis(analysis_id)
        if not analysis:
            return jsonify({"error": "Analysis not found"}), 404

        update_analysis_status(analysis_id, "processing")

        filepath = os.path.join(UPLOAD_DIR, analysis.get("stored_path", ""))
        if not os.path.exists(filepath):
            update_analysis_status(analysis_id, "error")
            return jsonify({"error": "Dataset file not found on server"}), 404

        df = pd.read_csv(filepath)
        text_col = text_column or analysis.get("text_column") or df.columns[0]
        rating_col = rating_column or analysis.get("rating_column")

        if text_col not in df.columns:
            update_analysis_status(analysis_id, "error")
            return jsonify({"error": f"Column '{text_col}' not found. Available: {df.columns.tolist()}"}), 400

        ml_results = run_full_pipeline(df, text_col, rating_col)

        problems = detect_problems(
            ml_results["predictions"],
            ml_results["feature_names"],
        )

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
            except Exception:
                pass
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# ──────────────────────────────────────────────
# Get Results
# ──────────────────────────────────────────────
@app.route("/api/results/<analysis_id>")
def results(analysis_id):
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
# Get Predictions (paginated)
# ──────────────────────────────────────────────
@app.route("/api/predictions/<analysis_id>")
def predictions(analysis_id):
    try:
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)
        sentiment = request.args.get("sentiment", None)

        data = get_predictions(analysis_id, limit, offset, sentiment)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch predictions: {str(e)}"}), 500


# ──────────────────────────────────────────────
# List Analyses
# ──────────────────────────────────────────────
@app.route("/api/analyses")
def analyses():
    try:
        return jsonify(list_analyses())
    except Exception as e:
        return jsonify({"error": f"Failed to list analyses: {str(e)}"}), 500


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
