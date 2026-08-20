"""
Spam / Fake Review Detector
Flags suspicious reviews using heuristic and NLP checks.
Produces a spam_score (0.0 – 1.0) and is_flagged boolean for each review.
"""

import re
from collections import Counter


# ── Heuristic thresholds ──
MIN_REVIEW_LENGTH = 5
GENERIC_PHRASES = [
    "good product", "great product", "love it", "best product", "highly recommend",
    "amazing product", "wonderful product", "excellent product", "perfect product",
    "great item", "love this", "best buy", "awesome", "fantastic", "superb",
    "great service", "fast delivery", "highly recommended", "five stars",
    "10/10", "must buy", "no complaints", "works great", "amazing",
    "terrible product", "worst product", "do not buy", "waste of money",
    "very bad", "horrible", "awful", "worst ever", "never again",
    "good", "great", "nice", "bad", "terrible", "excellent", "poor",
]

KEYWORD_STUFF_PATTERNS = [
    r"(\b\w+\b)\s+\1\s+\1",                    # same word 3+ times: "good good good"
    r"[!]{3,}",                                  # excessive exclamation: "!!!"
    r"[A-Z\s]{10,}",                            # all caps blocks
    r"(buy|purchase|order|visit|click|link|free|discount|offer|deal|promo){3,}",  # promotional spam
]


def _text_length_score(text: str) -> float:
    """Shorter reviews are more suspicious."""
    length = len(text.strip())
    if length < MIN_REVIEW_LENGTH:
        return 1.0
    if length < 20:
        return 0.7
    if length < 40:
        return 0.3
    return 0.0


def _genericness_score(text: str) -> float:
    """Check if review is overly generic with no substance."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower().strip())
    words = cleaned.split()
    if not words:
        return 1.0

    word_set = set(words)
    generic_matches = sum(1 for phrase in GENERIC_PHRASES if phrase in cleaned)
    total_generic_words = sum(len(phrase.split()) for phrase in GENERIC_PHRASES if phrase in cleaned)
    generic_ratio = total_generic_words / max(len(words), 1)

    unique_ratio = len(word_set) / max(len(words), 1)

    score = 0.0
    if generic_ratio > 0.8:
        score += 0.6
    elif generic_ratio > 0.5:
        score += 0.3

    if unique_ratio < 0.3:
        score += 0.3
    elif unique_ratio < 0.5:
        score += 0.15

    if generic_matches >= 3:
        score += 0.3
    elif generic_matches >= 2:
        score += 0.15

    return min(score, 1.0)


def _repetition_score(text: str) -> float:
    """Detect word and phrase repetition."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    words = cleaned.split()
    if len(words) < 2:
        return 0.0

    word_counts = Counter(words)
    most_common_count = word_counts.most_common(1)[0][1]
    repetition_ratio = most_common_count / len(words)

    score = 0.0
    if repetition_ratio > 0.4:
        score += 0.7
    elif repetition_ratio > 0.25:
        score += 0.4
    elif repetition_ratio > 0.15:
        score += 0.2

    for pattern in KEYWORD_STUFF_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            score += 0.25
            break

    return min(score, 1.0)


def _sentiment_extreme_score(text: str, sentiment: str) -> float:
    """Extreme sentiment with very short text is suspicious."""
    length = len(text.strip())
    if sentiment in ("positive", "negative") and length < 15:
        return 0.5
    return 0.0


def _caps_and_punctuation_score(text: str) -> float:
    """Excessive caps or punctuation suggests spam or bot."""
    if not text:
        return 0.0
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    excl_count = text.count("!") + text.count("?")

    score = 0.0
    if caps_ratio > 0.6:
        score += 0.5
    elif caps_ratio > 0.4:
        score += 0.25
    if excl_count > 5:
        score += 0.3
    elif excl_count > 3:
        score += 0.15
    return min(score, 1.0)


def _url_and_promo_score(text: str) -> float:
    """Detect URLs, promo codes, and promotional language."""
    cleaned = text.lower()
    score = 0.0

    if re.search(r"https?://|www\.|\.com|\.net|\.org", cleaned):
        score += 0.5
    if re.search(r"\b\d{5,}\b", cleaned):  # long numbers (promo codes)
        score += 0.2
    promo_words = ["coupon", "discount", "promo", "code", "free shipping",
                   "limited offer", "act now", "subscribe", "click here"]
    if any(w in cleaned for w in promo_words):
        score += 0.3

    return min(score, 1.0)


def compute_spam_score(text: str, sentiment: str = "neutral") -> float:
    """Compute composite spam score (0.0 = clean, 1.0 = definitely spam)."""
    scores = [
        (_text_length_score(text), 0.15),
        (_genericness_score(text), 0.25),
        (_repetition_score(text), 0.20),
        (_sentiment_extreme_score(text, sentiment), 0.10),
        (_caps_and_punctuation_score(text), 0.15),
        (_url_and_promo_score(text), 0.15),
    ]

    weighted_sum = sum(score * weight for score, weight in scores)
    total_weight = sum(weight for _, weight in scores)

    return round(weighted_sum / total_weight, 3)


def detect_spam(predictions: list[dict], threshold: float = 0.55) -> list[dict]:
    """Add spam_score and is_flagged to each prediction dict. Returns the same list."""
    for pred in predictions:
        text = str(pred.get("text", pred.get("review_text", "")))
        sentiment = pred.get("sentiment", "neutral")
        score = compute_spam_score(text, sentiment)
        pred["spam_score"] = score
        pred["is_flagged"] = score >= threshold
    return predictions


def detect_duplicates(predictions: list[dict]) -> list[dict]:
    """Mark exact duplicate reviews as flagged."""
    seen: dict[str, int] = {}
    for pred in predictions:
        text = str(pred.get("text", pred.get("review_text", ""))).strip().lower()
        if text in seen:
            seen[text] += 1
            pred["is_flagged"] = True
            pred["spam_score"] = max(pred.get("spam_score", 0.0), 0.8)
        else:
            seen[text] = 1
    return predictions
