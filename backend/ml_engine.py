"""
ML Engine: Text cleaning, TF-IDF vectorization, model training, and sentiment prediction.
Supports optional Transformer (DistilBERT) models and custom problem categories.
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
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, accuracy_score

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


def _generate_labels_from_text(texts: list[str]) -> list[str]:
    try:
        from textblob import TextBlob
        labels = []
        for t in texts:
            polarity = TextBlob(str(t)).sentiment.polarity
            if polarity > 0.1:
                labels.append("positive")
            elif polarity < -0.1:
                labels.append("negative")
            else:
                labels.append("neutral")
        return labels
    except ImportError:
        return ["neutral"] * len(texts)


def build_tfidf(texts: list[str], max_features: int = 5000):
    min_df = 2 if len(texts) >= 20 else 1
    vectorizer = TfidfVectorizer(max_features=max_features, ngram_range=(1, 2), min_df=min_df, max_df=0.95)
    X = vectorizer.fit_transform(texts)
    return X, vectorizer


def train_models(X, y):
    counts = Counter(y)
    min_count = min(counts.values())
    stratify_param = y if min_count >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify_param)

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


def _run_transformer_pipeline(texts: list[str], labels: list[str], progress_cb=None):
    try:
        import torch
        from transformers import pipeline as hf_pipeline

        if progress_cb:
            progress_cb("Loading transformer model", 40)

        device = 0 if torch.cuda.is_available() else -1
        model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
        classifier = hf_pipeline(
            "sentiment-analysis",
            model=model_name,
            device=device,
            truncation=True,
            max_length=512,
        )

        label_map = {"positive": "positive", "negative": "negative", "neutral": "neutral",
                      "label_0": "negative", "label_1": "neutral", "label_2": "positive",
                      "pos": "positive", "neg": "negative"}

        predictions = []
        batch_size = 64 if torch.cuda.is_available() else 16
        for i in range(0, len(texts), batch_size):
            batch = [str(t)[:512] for t in texts[i:i + batch_size]]
            results = classifier(batch)
            for r in results:
                raw_label = r["label"].lower()
                predictions.append(label_map.get(raw_label, "neutral"))
            if progress_cb:
                pct = 40 + int((i + len(batch)) / len(texts) * 30)
                progress_cb("Running transformer predictions", min(pct, 70))

        sentiment_counts = Counter(predictions)
        total = len(predictions)
        sentiment_distribution = {
            "positive": sentiment_counts.get("positive", 0),
            "negative": sentiment_counts.get("negative", 0),
            "neutral": sentiment_counts.get("neutral", 0),
            "total": total,
        }

        predictions_with_text = [
            {"text": texts[i], "sentiment": predictions[i], "cleaned": texts[i]}
            for i in range(len(predictions))
        ]

        return {
            "models": {"transformer": {"accuracy": 0, "report": {}}},
            "best_model": "transformer",
            "best_accuracy": 0,
            "sentiment_distribution": sentiment_distribution,
            "predictions": predictions_with_text,
            "feature_names": [],
            "labels": labels,
            "cleaned_texts": texts,
        }
    except Exception as e:
        raise ValueError(f"Transformer pipeline failed: {e}. Falling back to TF-IDF.")


def run_full_pipeline(df: pd.DataFrame, text_column: str, rating_column: str = None,
                      progress_cb=None, custom_categories: dict = None,
                      use_transformer: bool = False):
    texts = df[text_column].fillna("").tolist()

    if rating_column and rating_column in df.columns:
        labels = [detect_sentiment_from_rating(r) for r in df[rating_column].tolist()]
    else:
        labels = _generate_labels_from_text(texts)

    if progress_cb:
        progress_cb("Cleaning text", 10)

    cleaned_texts = [clean_text(t) for t in texts]

    valid_mask = [bool(t.strip()) for t in cleaned_texts]
    cleaned_texts = [t for t, v in zip(cleaned_texts, valid_mask) if v]
    labels = [l for l, v in zip(labels, valid_mask) if v]
    original_texts = [t for t, v in zip(texts, valid_mask) if v]

    if len(cleaned_texts) < 10:
        raise ValueError("Not enough valid reviews for analysis (minimum 10 required).")

    if use_transformer:
        try:
            result = _run_transformer_pipeline(original_texts, labels, progress_cb)
            result["cleaned_texts"] = cleaned_texts
            return result
        except ValueError:
            pass

    if progress_cb:
        progress_cb("Building TF-IDF matrix", 20)

    X, vectorizer = build_tfidf(cleaned_texts)

    if progress_cb:
        progress_cb("Training models", 35)

    trained_models, results, best_name = train_models(X, labels)
    best_model = trained_models[best_name]

    if progress_cb:
        progress_cb("Making predictions", 60)

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

    if progress_cb:
        progress_cb("Training complete", 70)

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
