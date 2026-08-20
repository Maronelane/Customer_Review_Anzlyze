"""
Root Cause Clustering
Groups similar negative/neutral reviews into root cause clusters using
TF-IDF vectorization + MiniBatchKMeans (fast), with keyword-based dynamic labels.
"""

import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score


MAX_CLUSTERABLE = 3000
MIN_CLUSTER_SIZE = 3


def _clean_for_clustering(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_cluster_label(texts: list[str], top_n: int = 4) -> str:
    if not texts:
        return "Uncategorized"

    sample = texts[:200]
    vectorizer = TfidfVectorizer(
        max_features=300,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.9,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(sample)
    except ValueError:
        return "Uncategorized"

    feature_names = vectorizer.get_feature_names_out()
    mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
    top_indices = mean_tfidf.argsort()[::-1][:top_n]
    keywords = [feature_names[i] for i in top_indices if mean_tfidf[i] > 0]

    if not keywords:
        return "Uncategorized"

    return " / ".join(kw.title() for kw in keywords[:3])


def cluster_reviews(
    predictions: list[dict],
    min_cluster_size: int = MIN_CLUSTER_SIZE,
    max_k: int = 15,
) -> list[dict]:
    clusterable = [
        (i, p) for i, p in enumerate(predictions)
        if p.get("sentiment") in ("negative", "neutral")
    ]

    for i, p in enumerate(predictions):
        p["cluster_id"] = -1
        p["cluster_label"] = ""

    if len(clusterable) < min_cluster_size * 2:
        return predictions

    if len(clusterable) > MAX_CLUSTERABLE:
        import random
        random.seed(42)
        sampled_indices = random.sample(range(len(clusterable)), MAX_CLUSTERABLE)
        sampled = [clusterable[i] for i in sampled_indices]
    else:
        sampled = clusterable
        sampled_indices = list(range(len(clusterable)))

    texts = [_clean_for_clustering(str(p.get("text", p.get("review_text", "")))) for _, p in sampled]
    texts = [t for t in texts if len(t) > 5]

    if len(texts) < min_cluster_size * 2:
        return predictions

    vectorizer = TfidfVectorizer(
        max_features=1500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.85,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return predictions

    n_clusters = min(max_k, max(2, len(texts) // 15))

    try:
        km = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=1000, n_init=3)
        labels = km.fit_predict(tfidf_matrix)
    except Exception:
        return predictions

    try:
        if len(set(labels)) > 1 and len(labels) > n_clusters:
            score = silhouette_score(tfidf_matrix, labels, sample_size=min(5000, len(labels)))
            if score < 0.05:
                return predictions
    except Exception:
        pass

    cluster_texts: dict[int, list[str]] = {}
    for idx, label in enumerate(labels):
        if label not in cluster_texts:
            cluster_texts[label] = []
        cluster_texts[label].append(texts[idx])

    cluster_labels: dict[int, str] = {}
    for cid, ctexts in cluster_texts.items():
        if len(ctexts) >= min_cluster_size:
            cluster_labels[cid] = _extract_cluster_label(ctexts)
        else:
            cluster_labels[cid] = "Minor Issue"

    for idx_in_sampled, (orig_idx, pred) in enumerate(sampled):
        if idx_in_sampled < len(labels):
            label = labels[idx_in_sampled]
            if len(cluster_texts.get(label, [])) >= min_cluster_size:
                pred["cluster_id"] = int(label)
                pred["cluster_label"] = cluster_labels.get(label, "Uncategorized")

    return predictions


def get_cluster_summary(predictions: list[dict]) -> list[dict]:
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
        c["severity"] = "high" if neg_pct > 60 else "medium" if neg_pct > 30 else "low"

    return result
