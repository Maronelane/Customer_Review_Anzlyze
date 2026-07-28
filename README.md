# AnZlyze — Customer Review Intelligence Platform

A web application that reads thousands of customer reviews, performs sentiment analysis using TF-IDF + Machine Learning, detects common problems, and generates actionable business recommendations.

## System Flow

```
Upload CSV → Text Cleaning → TF-IDF Vectorization → ML Training → Sentiment Prediction → Problem Detection → Recommendations → Dashboard
```

## Tech Stack

- **Backend:** Flask (Python 3.x) + SQLite
- **Frontend:** React 18 + TypeScript + Vite
- **ML:** scikit-learn (Logistic Regression, Naive Bayes, SVM) + NLTK + TF-IDF
- **Charts:** Recharts

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
# Flask runs on http://localhost:5001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Vite dev server on http://localhost:5173 (proxies /api → :5001)
```

## CSV Format

Your CSV should have at least a text column containing customer reviews:

```csv
review_text,rating
"Great product, love it!",5
"Terrible quality, broke after 1 day",1
"Average, nothing special",3
```

The system auto-detects columns matching patterns like `review`, `text`, `comment`, `rating`, `score`, `star`.

## Features

- **Dataset Upload** — Drag-and-drop CSV upload with column preview
- **Text Cleaning** — Lowercase, special char removal, stopwords, lemmatization
- **TF-IDF Vectorization** — Unigram + bigram feature extraction
- **ML Models** — Auto-selects best from Logistic Regression, Naive Bayes, SVM
- **Sentiment Prediction** — Positive / Negative / Neutral classification
- **Problem Detection** — Extracts common complaint categories from negative reviews
- **Business Recommendations** — Prioritized actionable suggestions
- **Interactive Dashboard** — Pie charts, bar charts, review tables with pagination

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/upload` | Upload CSV dataset |
| POST | `/api/analyze` | Run ML pipeline |
| GET | `/api/results/<id>` | Get analysis results |
| GET | `/api/predictions/<id>` | Get paginated predictions |
| GET | `/api/analyses` | List all analyses |
