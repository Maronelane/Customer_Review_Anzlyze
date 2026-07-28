"""
Problem Detector: Extracts common problems/themes from negative customer reviews.
"""
from collections import Counter
import re
import numpy as np


PROBLEM_KEYWORDS = {
    "delivery": ["delivery", "shipping", "late", "slow", "delayed", "package", "arrived", "courier", "track", "lost"],
    "quality": ["quality", "broken", "defective", "damage", "cheap", "flimsy", "fell apart", "poor", "bad", "terrible"],
    "price": ["price", "expensive", "overpriced", "cost", "value", "waste", "money", "rip off", "not worth"],
    "customer_service": ["service", "support", "rude", "help", "response", "wait", "hold", "agent", "representative", "refund"],
    "product": ["product", "missing", "wrong", "different", "description", "expected", "fake", "counterfeit", "size", "fit"],
    "usability": ["difficult", "complicated", "confusing", "hard to use", "unintuitive", "interface", "design", "bug", "crash", "error"],
    "food_taste": ["taste", "flavor", "bland", "stale", "expired", "fresh", "delicious", "awful", "disgusting"],
    "comfort": ["comfortable", "uncomfortable", "tight", "loose", "itchy", "irritate", "rash", "allergy"],
}


def detect_problems(predictions: list[dict], feature_names: list[str], top_n: int = 15):
    negative_reviews = [p for p in predictions if p["sentiment"] == "negative"]

    if not negative_reviews:
        return {
            "problems": [],
            "problem_count": 0,
            "total_negative": 0,
            "top_complaint_words": [],
        }

    negative_texts = " ".join([p["cleaned"] for p in negative_reviews])
    words = negative_texts.split()
    word_freq = Counter(words).most_common(50)

    problem_scores = {}
    problem_examples = {}

    for category, keywords in PROBLEM_KEYWORDS.items():
        score = 0
        examples = []
        for word, freq in word_freq:
            if word in keywords:
                score += freq
        for review in negative_reviews:
            text_lower = review["cleaned"].lower()
            for keyword in keywords:
                if keyword in text_lower:
                    if len(examples) < 3:
                        examples.append(review["text"][:200])
                    break
        if score > 0:
            problem_scores[category] = score
            problem_examples[category] = examples

    tfidf_negative_indices = []
    all_cleaned = [p["cleaned"] for p in predictions]
    for i, p in enumerate(predictions):
        if p["sentiment"] == "negative":
            tfidf_negative_indices.append(i)

    top_tfidf_words = []
    if feature_names and len(negative_reviews) > 0:
        neg_words = Counter()
        for review in negative_reviews:
            for word in review["cleaned"].split():
                if word in feature_names:
                    neg_words[word] += 1
        top_tfidf_words = [{"word": w, "count": c} for w, c in neg_words.most_common(top_n)]

    sorted_problems = sorted(problem_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for category, score in sorted_problems:
        severity = "high" if score > len(negative_reviews) * 0.3 else "medium" if score > len(negative_reviews) * 0.1 else "low"
        results.append({
            "category": category.replace("_", " ").title(),
            "category_key": category,
            "frequency": score,
            "severity": severity,
            "percentage": round(score / max(len(negative_reviews), 1) * 100, 1),
            "examples": problem_examples.get(category, []),
        })

    return {
        "problems": results[:top_n],
        "problem_count": len(results),
        "total_negative": len(negative_reviews),
        "top_complaint_words": top_tfidf_words,
        "negative_review_sample": [p["text"][:300] for p in negative_reviews[:10]],
    }
