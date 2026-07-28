"""
ML Engine: Text cleaning, TF-IDF vectorization, model training, and sentiment prediction.
"""
import re
import string
import pickle
import os
from collections import Counter

import nltk
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline

MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(MODELS_DIR, exist_ok=True)

_lemmatizer = None
_stop_words = None


def _get_nltk_resources():
    global _lemmatizer, _stop_words
    if _lemmatizer is None:
        for pkg in ["punkt", "punkt_tab", "wordnet", "stopwords", "omw-1.4"]:
            try:
                nltk.data.find(f"tokenizers/{pkg}" if "punkt" in pkg else f"corpora/{pkg}")
            except LookupError:
                nltk.download(pkg, quiet=True)
        _lemmatizer = WordNetLemmatizer()
        _stop_words = set(stopwords.words("english"))
    return _lemmatizer, _stop_words


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"\d+", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()

    lemmatizer, stop_words = _get_nltk_resources()
    tokens = word_tokenize(text)
    tokens = [lemmatizer.lemmatize(t) for t in tokens if t not in stop_words and len(t) > 2]
    return " ".join(tokens)


def detect_sentiment_from_rating(rating) -> str:
    try:
        r = float(rating)
    except (TypeError, ValueError):
        return "neutral"
    if r >= 4:
        return "positive"
    elif r <= 2:
        return "negative"
    return "neutral"


def build_tfidf(texts: list[str], max_features: int = 5000):
    vectorizer = TfidfVectorizer(max_features=max_features, ngram_range=(1, 2), min_df=2, max_df=0.95)
    X = vectorizer.fit_transform(texts)
    return X, vectorizer


def train_models(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    models = {
        "logistic_regression": LogisticRegression(max_iter=1000, C=1.0, random_state=42),
        "naive_bayes": MultinomialNB(alpha=0.1),
        "svm": LinearSVC(max_iter=2000, C=1.0, random_state=42),
    }

    results = {}
    trained = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        results[name] = {
            "accuracy": round(acc, 4),
            "report": report,
        }
        trained[name] = model

    best_name = max(results, key=lambda k: results[k]["accuracy"])
    return trained, results, best_name


def save_model(model, vectorizer, analysis_id: str):
    path = os.path.join(MODELS_DIR, f"{analysis_id}.pkl")
    with open(path, "wb") as f:
        pickle.dump({"model": model, "vectorizer": vectorizer}, f)


def load_model(analysis_id: str):
    path = os.path.join(MODELS_DIR, f"{analysis_id}.pkl")
    if not os.path.exists(path):
        return None, None
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["model"], data["vectorizer"]


def predict_sentiment(texts: list[str], model, vectorizer) -> list[str]:
    cleaned = [clean_text(t) for t in texts]
    X = vectorizer.transform(cleaned)
    return model.predict(X).tolist()


def run_full_pipeline(df: pd.DataFrame, text_column: str, rating_column: str = None):
    texts = df[text_column].fillna("").tolist()

    if rating_column and rating_column in df.columns:
        labels = [detect_sentiment_from_rating(r) for r in df[rating_column].tolist()]
    else:
        labels = [detect_sentiment_from_rating(3)] * len(texts)

    cleaned_texts = [clean_text(t) for t in texts]

    valid_mask = [bool(t.strip()) for t in cleaned_texts]
    cleaned_texts = [t for t, v in zip(cleaned_texts, valid_mask) if v]
    labels = [l for l, v in zip(labels, valid_mask) if v]
    original_texts = [t for t, v in zip(texts, valid_mask) if v]

    if len(cleaned_texts) < 10:
        raise ValueError("Not enough valid reviews for analysis (minimum 10 required).")

    X, vectorizer = build_tfidf(cleaned_texts)
    trained_models, results, best_name = train_models(X, labels)
    best_model = trained_models[best_name]

    all_predictions = best_model.predict(X).tolist()

    sentiment_counts = Counter(all_predictions)
    total = len(all_predictions)
    sentiment_distribution = {
        "positive": sentiment_counts.get("positive", 0),
        "negative": sentiment_counts.get("negative", 0),
        "neutral": sentiment_counts.get("neutral", 0),
        "total": total,
    }

    feature_names = vectorizer.get_feature_names_out().tolist()
    predictions_with_text = [
        {"text": original_texts[i], "sentiment": all_predictions[i], "cleaned": cleaned_texts[i]}
        for i in range(len(all_predictions))
    ]

    return {
        "models": results,
        "best_model": best_name,
        "best_accuracy": results[best_name]["accuracy"],
        "sentiment_distribution": sentiment_distribution,
        "predictions": predictions_with_text,
        "feature_names": feature_names,
        "tfidf_matrix": X,
        "labels": labels,
        "cleaned_texts": cleaned_texts,
    }
