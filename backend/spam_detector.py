"""
Spam / Fake Review Detector

Philosophy: a review is only flagged as spam when there is a STRONG, objective
reason to believe it is not genuine. Short or generic reviews ("bad product",
"great") are NOT flagged on their own — real customers write short reviews all
the time.

We flag two clear-cut cases:
  1. PROMOTIONAL / LINK SPAM — reviews containing URLs, contact info, promo
     codes, or affiliate/buy-now language.
  2. DUPLICATES — identical (or near-identical) review text repeated many times
     in the dataset. This is the classic fake-review / bot signal. A short,
     generic review IS treated as spam only when it is duplicated.

Each review gets:
  - spam_score:       0.0 (genuine) .. 1.0 (definitely spam)
  - spam_confidence:  high / medium / low
  - spam_reasons:     list of { signal, detail } explaining why
  - is_flagged:       boolean
"""

import re
from collections import Counter

FLAG_THRESHOLD = 0.55
# Duplicate detection: identical (normalized) text must appear at least this many
# times before it is flagged.
DUPLICATE_MIN_COPIES = 10
# A duplicate is only spam if it is SUBSTANTIVE. Millions of real customers
# write ultra-short praise ("good", "nice", "super", "great product") and a
# handful of those texts happen to repeat many times in real datasets — that
# genuine crowd behaviour is NOT spam. So a repeated text must carry enough real
# content (this many words) before we consider it a possible copy-paste bot
# campaign. Repeated short praise is never flagged, no matter how many copies.
MIN_SUBSTANTIVE_WORDS = 6
# Score given to a duplicated (and substantive) review.
DUPLICATE_SCORE = 0.85


class _Reasons:
    def __init__(self):
        self.items = []

    def add(self, signal, detail):
        self.items.append({"signal": signal, "detail": detail})

    def as_list(self):
        return self.items


# ── Signal A: Promotional / link / contact spam ──
# These are INTENT-BASED phrases used to solicit / self-promote / advertise.
# Genuine customers praising a product almost never say these things, so a hit is
# a safe "decisive" signal. Ordinary enthusiasm or praise ("best deal", "great
# price", "hurry", "going to buy now", "my next order now") is NOT here — that is
# everyday customer language, not promotional spam.
_PROMO_PHRASES = [
    # Affiliate / self-promotion / solicitation with intent
    "link in bio", "click the link", "click this link", "click on the link",
    "open the link", "check out my", "visit my", "follow me", "dm me",
    "contact me", "whatsapp me", "my whatsapp", "my telegram", "my instagram",
    "my youtube", "my channel", "order from my", "buy from my", "sold on my",
    "available on my", "affiliate", "referral link", "referral code",
    # Coupon / deal codes (not just the word "coupon" alone — require intent)
    "coupon code", "discount code", "promo code", "offer code", "promo code",
]
# A superset used by the duplicate/substantive check so a repeated text full of
# promotional intent is treated as spam even if short.
_PROMO_WORDS = _PROMO_PHRASES


def _promo_score(text, reasons: _Reasons) -> float:
    """Flag promotional / link / contact spam. Strong, objective signal.

    Only explicit, intent-revealing promotional content is flagged. A genuine
    review that happens to say "best deal" or "I'm going to buy now" is praise,
    not spam, and is never flagged here."""
    cleaned = (text or "").lower()

    # URL: a real scheme or "www." followed by a true domain, or a bare domain
    # with a TLD or path. Crucially this must NOT match "wowwww" or "wow..." —
    # we require "www." to be followed by a letter/number domain character.
    if re.search(r"https?://", cleaned):
        reasons.add("Contains URL", "Includes a web link")
        return 0.95
    if re.search(r"\bwww\.[a-z0-9][a-z0-9\-]*\.[a-z]{2,}", cleaned):
        reasons.add("Contains URL", "Includes a website link")
        return 0.95

    # Email: requires a real-looking local part then a domain TLD.
    if re.search(r"\b[\w.!#$%&'*+/=?^`{|}~-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.(?:com|net|org|io|co|in|edu|gov|me|biz|info|xyz|online|site|shop|store)\b", cleaned):
        reasons.add("Contact info", "Contains an email address")
        return 0.9

    # Phone number: a phone-like number is 9-15 digits total, optionally with
    # a leading '+' and grouped by spaces/hyphens. Deliberately does NOT match
    # short prices (e.g. "1299", "1100-1300", "@400").
    for m in re.finditer(r"(?:\+?\d[\s\-]?){8,}\d", cleaned):
        digits = len(re.sub(r"\D", "", m.group()))
        separators = len(re.sub(r"\d", "", m.group()))
        # Real phones: 9-15 digits with at most a few grouping separators.
        # Excludes long price strings and date-like sequences.
        if 9 <= digits <= 15 and separators <= 4:
            reasons.add("Contact info", "Contains a phone number")
            return 0.8

    # Intent-revealing promotional phrases. Genuine product praise doesn't say
    # "link in bio", "dm me", "coupon code", "subscribe to my channel", etc.
    hits = [w for w in _PROMO_PHRASES if w in cleaned]
    if hits:
        reasons.add("Promotional", f"Uses promotional/solicitation language: {', '.join(hits[:3])}")
        return 0.75

    return 0.0


# ── Signal B: Duplication (handled in detect_duplicates, not per-review) ──


# ── Signal C: Weak/advisory signals (never flag on their own) ──
# These can nudge a score upward ONLY when a strong signal is already present,
# but they are weighted so low that they can never push a genuine review past
# the flag threshold by themselves.

def _weak_signals(text, reasons: _Reasons):
    """Return a small advisory score. Never enough to flag by itself."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower().strip())
    words = [w for w in cleaned.split() if len(w) > 1]
    if not words:
        return 0.0, reasons

    total = 0.0

    # Repetition of the same content word many times (e.g. "good good good")
    content = [w for w in words if w not in _STOPWORDS]
    if content:
        counts = Counter(content)
        w, c = counts.most_common(1)[0]
        if c >= 3 and c / len(content) > 0.5:
            reasons.add("Repetitive", f"'{w}' appears {c} times with little other content")
            total += 0.3

    # Excessive punctuation / ALL CAPS
    letters = [ch for ch in text if ch.isalpha()]
    if letters and sum(1 for ch in letters if ch.isupper()) / len(letters) > 0.7:
        reasons.add("Excessive caps", "Almost entirely capitalised")
        total += 0.25
    if (text or "").count("!") + (text or "").count("?") > 8:
        reasons.add("Excessive punctuation", "Large number of exclamation/question marks")
        total += 0.2

    return min(total, 1.0), reasons


_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "it", "this", "that", "with", "as", "was", "be", "my", "i",
    "me", "up", "all", "at", "by", "do", "we", "you", "he", "she", "they",
    "them", "are", "had", "has", "have", "so", "than", "its", "their",
    "im", "ive", "dont", "cant", "wont", "not", "no", "very", "really",
}


def compute_spam_details(text: str, sentiment: str = "neutral"):
    """Compute a conservative spam score. Promotional content is the only
    per-review signal that can flag. Everything else is advisory only."""
    text = str(text or "")
    reasons = _Reasons()

    promo = _promo_score(text, reasons)
    weak, _ = _weak_signals(text, reasons)

    # Promotional content is a strong, decisive signal.
    if promo > 0:
        spam_score = 0.55 + 0.35 * promo
        spam_score = min(round(spam_score, 3), 0.95)
    else:
        # No promotional content. Weak signals alone must NOT flag a review.
        spam_score = round(weak * 0.12, 3)

    severity = _severity(spam_score)
    return spam_score, severity, reasons.as_list()


def _severity(score):
    if score >= 0.8:
        return "high"
    if score >= FLAG_THRESHOLD:
        return "medium"
    return "low"


def compute_spam_score(text: str, sentiment: str = "neutral") -> float:
    """Backwards-compatible numeric-only score."""
    score, _, _ = compute_spam_details(text, sentiment)
    return score


def detect_spam(predictions: list[dict], threshold: float = FLAG_THRESHOLD) -> list[dict]:
    """Add spam_score, spam_confidence, spam_reasons, is_flagged for each review."""
    for pred in predictions:
        text = str(pred.get("text", pred.get("review_text", "")))
        sentiment = pred.get("sentiment", "neutral")
        score, severity, reasons = compute_spam_details(text, sentiment)
        pred["spam_score"] = score
        pred["spam_confidence"] = severity
        pred["spam_reasons"] = reasons
        pred["is_flagged"] = score >= threshold
    return predictions


def _normalize(text: str) -> str:
    """Normalize text for duplicate detection: lowercase, strip, collapse spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower().strip()))


def _is_substantive(norm_text: str) -> bool:
    """Is a repeated text substantive enough to be a likely bot campaign?

    Repeating ultra-short praise ("good", "nice", "super") across many reviews is
    normal human crowd behaviour, not spam. We only flag a duplicate once it
    carries real informational content (enough words) OR contains promotional /
    link / contact signals. This keeps the many genuine one-word "good" reviews
    clean while still catching classic copy-paste bot spam."""
    words = norm_text.split()
    if len(words) >= MIN_SUBSTANTIVE_WORDS:
        return True
    # Promotional / link / contact signals make even a short repeat suspicious.
    cleaned = norm_text
    if re.search(r"https?://|www\.", cleaned):
        return True
    if re.search(r"\b[\w.-]+@[\w.-]+\.(?:com|net|org|io|co|in|edu|gov|me|biz|info|xyz|online|site|shop|store)\b", cleaned):
        return True
    if re.search(r"(?:\+?\d[\s\-]?){8,}\d", cleaned):
        return True
    if any(w in cleaned for w in _PROMO_WORDS):
        return True
    return False


def detect_duplicates(predictions: list[dict],
                      min_copies: int = DUPLICATE_MIN_COPIES) -> list[dict]:
    """Flag duplicate reviews. A repeated review is treated as spam only when it
    is SUBSTANTIVE (carries real content or promotional signals). Ultra-short
    praise that many different customers happen to repeat ("good", "nice") is
    genuine crowd behaviour and is deliberately NOT flagged."""
    counts: dict[str, int] = {}
    for pred in predictions:
        norm = _normalize(str(pred.get("text", pred.get("review_text", ""))))
        counts[norm] = counts.get(norm, 0) + 1

    duplicated = {
        t for t, c in counts.items()
        if c >= min_copies and t and _is_substantive(t)
    }

    for pred in predictions:
        norm = _normalize(str(pred.get("text", pred.get("review_text", ""))))
        if norm in duplicated:
            copies = counts[norm]
            pred["is_flagged"] = True
            pred["spam_score"] = max(pred.get("spam_score", 0.0), DUPLICATE_SCORE)
            pred["spam_confidence"] = "high"
            # Replace any "no flags" reason with the real duplicate explanation.
            reasons = [r for r in pred.get("spam_reasons", []) if r.get("signal") != "OK"]
            dup = {"signal": "Duplicate review",
                   "detail": f"Identical text to {copies - 1} other review(s) — {copies} in total"}
            if not any(r.get("signal") == "Duplicate review" for r in reasons):
                reasons.insert(0, dup)
            pred["spam_reasons"] = reasons

    return predictions
