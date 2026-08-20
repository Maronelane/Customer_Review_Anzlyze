"""
Root Cause Clustering
Groups similar negative/neutral reviews into root cause clusters using
TF-IDF vectorization + DBSCAN, with keyword-based dynamic labels.
"""

import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity


def _clean_for_clustering(text: str) -> str:
    """Light cleaning for clustering input."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_cluster_label(texts: list[str], top_n: int = 4) -> str:
    """Extract a descriptive label from cluster's texts using TF-IDF keywords."""
    if not texts:
        return "Uncategorized"

    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.9,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return "Uncategorized"

    feature_names = vectorizer.get_feature_names_out()
    mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
    top_indices = mean_tfidf.argsort()[::-1][:top_n]
    keywords = [feature_names[i] for i in top_indices if mean_tfidf[i] > 0]

    if not keywords:
        return "Uncategorized"

    label_parts = [kw.title() for kw in keywords[:3]]
    return " / ".join(label_parts)


def cluster_reviews(
    predictions: list[dict],
    min_cluster_size: int = 3,
    eps: float = 0.4,
    min_samples: int = 2,
) -> list[dict]:
    """
    Cluster negative/neutral reviews and add cluster_id + cluster_label to each.
    Returns the updated predictions list.
    """

    clusterable = [
        (i, p) for i, p in enumerate(predictions)
        if p.get("sentiment") in ("negative", "neutral")
    ]

    if len(clusterable) < min_cluster_size:
        for i, p in enumerate(predictions):
            p["cluster_id"] = -1
            p["cluster_label"] = ""
        return predictions

    texts = [_clean_for_clustering(p.get("text", p.get("review_text", ""))) for _, p in clusterable]

    vectorizer = TfidfVectorizer(
        max_features=2000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.85,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        for i, p in enumerate(predictions):
            p["cluster_id"] = -1
            p["cluster_label"] = ""
        return predictions

    similarity_matrix = cosine_similarity(tfidf_matrix)
    distance_matrix = 1 - similarity_matrix
    np.fill_diagonal(distance_matrix, 0)
    distance_matrix = np.clip(distance_matrix, 0, 2)

    clustering = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric="precomputed",
        algorithm="auto",
    )
    labels = clustering.fit_predict(distance_matrix)

    cluster_texts: dict[int, list[str]] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue
        if label not in cluster_texts:
            cluster_texts[label] = []
        cluster_texts[label].append(texts[idx])

    cluster_labels: dict[int, str] = {}
    for cid, ctexts in cluster_texts.items():
        if len(ctexts) >= min_cluster_size:
            cluster_labels[cid] = _extract_cluster_label(ctexts)
        else:
            cluster_labels[cid] = "Minor Issue"

    for i, p in enumerate(predictions):
        p["cluster_id"] = -1
        p["cluster_label"] = ""

    for idx, (orig_idx, pred) in enumerate(clusterable):
        label = labels[idx]
        if label != -1:
            pred["cluster_id"] = int(label)
            pred["cluster_label"] = cluster_labels.get(label, "Uncategorized")

    return predictions


def get_cluster_summary(predictions: list[dict]) -> list[dict]:
    """Summarize clusters for display: label, count, sample reviews, dominant sentiment."""
    clusters: dict[int, dict] = {}

    for p in predictions:
        cid = p.get("cluster_id", -1)
        if cid == -1:
            continue
        if cid not in clusters:
            clusters[cid] = {
                "cluster_id": cid,
                "label": p.get("cluster_label", "Uncategorized"),
                "count": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "sample_reviews": [],
            }
        c = clusters[cid]
        c["count"] += 1
        sentiment = p.get("sentiment", "neutral")
        if sentiment in ("positive", "negative", "neutral"):
            c[sentiment] += 1
        text = p.get("text", p.get("review_text", ""))
        if len(c["sample_reviews"]) < 3 and text:
            c["sample_reviews"].append(text[:200])

    result = sorted(clusters.values(), key=lambda x: x["count"], reverse=True)
    for c in result:
        total = c["count"]
        neg_pct = round(c["negative"] / max(total, 1) * 100, 1)
        c["negative_pct"] = neg_pct
        if neg_pct > 60:
            c["severity"] = "high"
        elif neg_pct > 30:
            c["severity"] = "medium"
        else:
            c["severity"] = "low"

    return result
