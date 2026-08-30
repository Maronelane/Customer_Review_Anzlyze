"""
Spam / Fake Review Detector
Flags suspicious reviews using explainable heuristic and NLP checks.

Each review gets:
  - spam_score:   0.0 (genuine) to 1.0 (definitely spam), weighted composite
  - spam_confidence: human-readable risk level derived from the score
  - spam_reasons: list of dicts, each { signal, severity, detail } explaining
                  WHY a review was flagged (the individual contributing signals)
  - is_flagged:  boolean (score >= threshold)
"""

import re
from collections import Counter

# ── Thresholds ──
FLAG_THRESHOLD = 0.55
DUPLICATE_SCORE = 0.85


class _Reasons:
    """Collects flagged signals for explainable output."""

    def __init__(self):
        self.items = []

    def add(self, signal, detail):
        self.items.append({"signal": signal, "detail": detail})

    def as_list(self):
        return self.items


# ── Signal 1: Review content quality / length ──
def _quality_score(text, reasons: _Reasons) -> float:
    """Length is not inherently suspicious; very short reviews carry little
    substantive signal, so they only contribute a modest bump."""
    length = len(text.strip())
    if length < 5:
        reasons.add("Very short", f"Only {length} characters, too brief to be a genuine detailed review")
        return 0.9
    if length < 15:
        reasons.add("Very brief", f"Only {length} characters")
        return 0.5
    if length < 30:
        reasons.add("Brief", f"Only {length} characters")
        return 0.25
    return 0.0


# ── Signal 2: Genericness (no specific detail) ──
GENERIC_PHRASES = [
    "good product", "great product", "love it", "best product", "highly recommend",
    "amazing product", "wonderful product", "excellent product", "perfect product",
    "great item", "love this", "best buy", "awesome product", "fantastic product",
    "great service", "fast delivery", "highly recommended", "five stars",
    "10/10", "must buy", "no complaints", "works great", "amazing product",
    "very bad product", "worst product", "do not buy", "waste of money",
    "very bad", "worst ever", "never again", "good quality", "best quality",
    "nice product", "perfect", "recommend this", "love it love it",
    "great product must buy", "best thing ever", "works perfectly",
    "awesome product", "high quality product", "great value for money",
]

# Generic words that add little info when they dominate a review
GENERIC_WORDS = {
    "good", "great", "nice", "bad", "terrible", "excellent", "poor", "love",
    "best", "amazing", "awesome", "fantastic", "perfect", "wonderful", "superb",
    "product", "item", "thing", "really", "very", "highly", "recommend",
    "bad", "awful", "horrible", "worst", "waste", "buy", "bought", "quality",
    "value", "works", "working", "delivery", "service",
}


def _genericness_score(text, reasons: _Reasons) -> float:
    """Flag reviews made mostly of generic praise/criticism with no concrete detail."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower().strip())
    words = [w for w in cleaned.split() if len(w) > 1]
    if not words:
        return 0.0

    generic_word_count = sum(1 for w in words if w in GENERIC_WORDS)
    generic_ratio = generic_word_count / len(words)

    # Phrase-level genericness (template-sounding)
    phrase_hits = [p for p in GENERIC_PHRASES if p in cleaned]

    score = 0.0

    # A review that is entirely generic (every word is generic) is almost
    # always a template/fake review, regardless of length.
    if generic_ratio >= 0.95:
        reasons.add("Full template", "Whole review uses generic praise/criticism with zero specific detail")
        score += 0.95
    elif generic_ratio > 0.7:
        reasons.add("Generic wording", f"{int(generic_ratio * 100)}% of words are generic praise/criticism with no specifics")
        score += 0.6
    elif generic_ratio > 0.5:
        reasons.add("Generic wording", f"{int(generic_ratio * 100)}% of words are generic with little specific detail")
        score += 0.35

    if len(phrase_hits) >= 3:
        reasons.add("Template phrases", f"Contains {len(phrase_hits)} common template phrases like '{phrase_hits[0]}'")
        score += 0.4
    elif len(phrase_hits) == 2 and len(words) < 20:
        reasons.add("Template phrases", f"Contains multiple generic phrases: {', '.join(phrase_hits)}")
        score += 0.25

    # A very short review that is fully generic is a strong fake-review signal
    if generic_ratio >= 0.8 and len(words) <= 8:
        reasons.add("Short & generic", "Extremely short and made up entirely of generic phrases")
        score += 0.3

    return min(score, 1.0)


# ── Signal 3: Repetition / stuffing ──
KEYWORD_STUFF_PATTERNS = [
    (r"\b(\w+)\b(?:\s+\1){2,}", "repeated word 3+ times"),          # "good good good"
    (r"[!?]{3,}", "excessive exclamation/question marks"),           # "!!!" or "???!!!"
    (r"\b[A-Z]+\b(?:\s+[A-Z]+\b){4,}", "large block of ALL-CAPS words"),  # "BUY NOW CLICK HERE"
]

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "it", "this", "that", "with", "as", "was", "be", "my", "i",
    "me", "up", "all", "at", "by", "do", "we", "you", "he", "she", "they",
    "them", "are", "had", "has", "have", "so", "than", "its", "their",
    "im", "ive", "dont", "cant", "wont",
}


def _repetition_score(text, reasons: _Reasons) -> float:
    """Detect word/phrase repetition and stuffing (classic bot behavior)."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    words = cleaned.split()
    if len(words) < 2:
        return 0.0

    # Ignore high-frequency stopwords when judging repetition — "the the the"
    # is normal in some text, but content-word stuffing isn't.
    content_words = [w for w in words if w not in _STOPWORDS]
    if not content_words:
        content_words = words

    word_counts = Counter(content_words)
    most_common_word, most_common_count = word_counts.most_common(1)[0]
    repetition_ratio = most_common_count / len(content_words)

    score = 0.0
    if repetition_ratio > 0.4:
        reasons.add("Repetitive", f"'{most_common_word}' is {most_common_count}/{len(content_words)} of the words")
        score += 0.7
    elif repetition_ratio > 0.25:
        reasons.add("Repetitive", f"'{most_common_word}' repeated {most_common_count} times")
        score += 0.4
    elif repetition_ratio > 0.15 and most_common_count >= 2:
        reasons.add("Some repetition", f"'{most_common_word}' repeats")
        score += 0.15

    for pattern, label in KEYWORD_STUFF_PATTERNS:
        if re.search(pattern, text or ""):
            reasons.add("Stuffing", label)
            score += 0.25

    return min(score, 1.0)


# ── Signal 4: URL / promotional / contact info ──
def _url_and_promo_score(text, reasons: _Reasons) -> float:
    """Detect URLs, promo codes, contact details, and promotional language."""
    cleaned = (text or "").lower()

    if re.search(r"https?://|www\.", cleaned):
        reasons.add("Contains URL", "Includes a web link")
        return 0.9
    if re.search(r"\b[\w.-]+@[\w.-]+\.\w+\b", cleaned):
        reasons.add("Contact info", "Contains an email address")
        return 0.8
    if re.search(r"(?:\+?\d[-. ]?){7,}\d\b", cleaned):
        reasons.add("Contact info", "Contains a phone number")
        return 0.7
    if re.search(r"\b\d{5,}\b", cleaned):
        reasons.add("Promo code", "Contains a long number (looks like a promo/order code)")
        return 0.5

    promo_words = ["coupon", "discount", "promo", "click here", "free shipping",
                   "limited offer", "act now", "subscribe", "buy now", "deal",
                   "offer code", "enroll", "sign up", "referral", "link in bio"]
    hits = [w for w in promo_words if w in cleaned]
    if hits:
        reasons.add("Promotional", f"Uses promotional language: {', '.join(hits[:3])}")
        return 0.6

    return 0.0


# ── Signal 5: Excessive caps / punctuation ──
def _caps_punct_score(text, reasons: _Reasons) -> float:
    """Excessive caps or punctuation suggests bot / emotionally-driven spam."""
    if not text:
        return 0.0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    excl_count = text.count("!") + text.count("?")

    score = 0.0
    if caps_ratio > 0.7:
        reasons.add("Excessive caps", f"{int(caps_ratio * 100)}% of letters are capitalised")
        score += 0.5
    elif caps_ratio > 0.5:
        reasons.add("Excessive caps", "Large portion of the text is capitalised")
        score += 0.3
    if excl_count > 8:
        reasons.add("Excessive punctuation", f"{excl_count} exclamation/question marks")
        score += 0.4
    elif excl_count > 4:
        reasons.add("Excessive punctuation", f"{excl_count} exclamation/question marks")
        score += 0.2

    return min(score, 1.0)


# ── Signal 6: Extreme sentiment in tiny text ──
def _extreme_short_score(text, sentiment, reasons: _Reasons) -> float:
    """Strong positive/negative verdict with almost no detail is commonly a fake review."""
    length = len(text.strip())
    if sentiment in ("positive", "negative") and length < 20:
        reasons.add("Emotive & brief", "Strong sentiment with very little supporting detail")
        return 0.5
    return 0.0


# ── Weights per signal ──
def _weights():
    return {
        "quality": 0.10,
        "genericness": 0.24,
        "repetition": 0.16,
        "url_promo": 0.34,
        "caps_punct": 0.12,
        "extreme_short": 0.04,
    }


def compute_spam_details(text: str, sentiment: str = "neutral"):
    """Compute spam score and explainable reasons."""
    text = str(text or "")
    reasons = _Reasons()

    scores = {
        "quality": _quality_score(text, reasons),
        "genericness": _genericness_score(text, reasons),
        "repetition": _repetition_score(text, reasons),
        "url_promo": _url_and_promo_score(text, reasons),
        "caps_punct": _caps_punct_score(text, reasons),
        "extreme_short": _extreme_short_score(text, sentiment, reasons),
    }

    w = _weights()
    weighted_sum = sum(scores[k] * w[k] for k in scores)
    total_weight = sum(w.values())
    spam_score = round(weighted_sum / total_weight, 3)

    # Decisive-signal floor: some signals alone are strong enough that the
    # weighted dilution should not let a clearly-flagged review through.
    # A business result is that spam_score should never drop too low when a
    # very strong indicator is present (e.g. a URL, contact details, or a full
    # generic template).
    signals = {r["signal"] for r in reasons.items}
    decisive = signals & {"Contains URL", "Contact info", "Full template", "Duplicate review"}
    if decisive:
        spam_score = max(spam_score, 0.8)

    severity = _severity(spam_score)
    return spam_score, severity, reasons.as_list()


def _severity(score):
    if score >= 0.8:
        return "high"
    if score >= FLAG_THRESHOLD:
        return "medium"
    return "low"


def compute_spam_score(text: str, sentiment: str = "neutral") -> float:
    """Backwards-compatible: return just the numeric spam score."""
    score, _, _ = compute_spam_details(text, sentiment)
    return score


def detect_spam(predictions: list[dict], threshold: float = FLAG_THRESHOLD) -> list[dict]:
    """Add spam_score, spam_confidence, spam_reasons, and is_flagged to each prediction."""
    for pred in predictions:
        text = str(pred.get("text", pred.get("review_text", "")))
        sentiment = pred.get("sentiment", "neutral")
        score, severity, reasons = compute_spam_details(text, sentiment)
        pred["spam_score"] = score
        pred["spam_confidence"] = severity
        pred["spam_reasons"] = reasons if reasons else [{"signal": "No flags", "detail": "No suspicious patterns detected"}]
        pred["is_flagged"] = score >= threshold
    return predictions


def detect_duplicates(predictions: list[dict]) -> list[dict]:
    """Mark duplicate reviews as flagged using a normalized-phrase fingerprint."""
    seen: dict[str, int] = {}
    for pred in predictions:
        text = str(pred.get("text", pred.get("review_text", ""))).strip().lower()
        if not text:
            seen[text] = seen.get(text, 0) + 1
            continue
        if text in seen:
            seen[text] += 1
            pred["is_flagged"] = True
            pred["spam_score"] = max(pred.get("spam_score", 0.0), DUPLICATE_SCORE)
            pred["spam_confidence"] = "high"
            claimed = pred.get("spam_reasons", [])
            dup_reason = {"signal": "Duplicate review", "detail": f"Identical to another review in this dataset ({seen[text]} copies found)"}
            if not any(r.get("signal") == "Duplicate review" for r in claimed):
                claimed = list(claimed)
                claimed.insert(0, dup_reason)
            pred["spam_reasons"] = claimed
        else:
            seen[text] = 1
    return predictions
