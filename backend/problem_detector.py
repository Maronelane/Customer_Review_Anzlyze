import re
from collections import Counter

# Universal & Electronics Problem Categories tailored for real-world reviews
# Prefer SPECIFIC phrases over bare generic words (e.g. don't use bare "quality"
# or "bad", which would misclassify any sound/battery quality complaint as a
# build-quality issue).
UNIVERSAL_PROBLEM_CATEGORIES = {
    # --- Quality & Craftsmanship ---
    "build_quality": [
        "build quality", "material quality", "poor quality", "bad quality",
        "quality is bad", "quality is poor", "cheap quality", "flimsy", "cheaply made",
        "shoddy", "weak", "fragile", "subpar", "inferior", "rubbish", "trash product",
        "broken", "broke", "defective", "damage", "fell apart", "falls apart",
        "cheap plastic", "poor built",
    ],

    # --- Performance & Reliability ---
    "performance_and_reliability": [
        "slow", "lagging", "sluggish", "performance", "unresponsive", "freezing",
        "glitch", "freeze", "crash", "error", "bug", "stopped", "fails",
        "not working", "not_working", "does not work", "stopped working",
        "did not work", "rebooting", "overheat", "heating", "battery drains",
        "battery drain", "dies quickly", "dead on arrival", "died", "power off",
    ],

    # --- Usability & Experience ---
    "usability_and_experience": [
        "difficult to", "hard to use", "complicated", "confusing", "unintuitive",
        "complex", "annoying", "uncomfortable", "awkward", "pain to", "not comfortable",
        "uncomfortable to", "hard to",
    ],

    # --- Customer Service & Support ---
    "customer_service": [
        "customer service", "customer care", "support", "rude staff", "unhelpful",
        "no response", "ignored", "no reply", "no support", "service is bad",
        "bad service", "poor service", "third class", "cheated", "fraud", "scam",
    ],

    # --- Shipping, Delivery & Packaging ---
    "shipping_and_packaging": [
        "delivery", "shipping", "delayed", "late delivery", "package", "arrived",
        "courier", "not received", "never received", "lost", "box", "crushed",
        "damaged box", "packing", "seal broken", "open box", "late",
    ],

    # --- Pricing & Value ---
    "pricing_and_value": [
        "overpriced", "not worth", "not_worth", "waste of money", "waste money",
        "rip off", "overcharged", "too expensive", "expensive", "price is high",
        "not worth the price", "value for money", "not value for money",
    ],

    # --- Product Accuracy & Description ---
    "product_accuracy": [
        "missing", "wrong item", "different from", "not as described", "not as pictured",
        "not_worth", "misleading", "fake", "counterfeit", "inauthentic", "not original",
        "duplicate", "received used", "used product", "not as expected", "not received",
        "different product",
    ],

    # --- Core Functionality / Feature Failures ---
    "functional_issues": [
        "not working", "not_working", "sound issue", "no sound", "audio issue",
        "mic issue", "mic not", "no mic", "volume issue", "no volume",
        "connection issue", "bluetooth issue", "disconnect", "not connecting",
        "won't connect", "no connectivity", "feature missing", "missing feature",
        "not function", "does not function", "fails",
    ]
}


def detect_problems(predictions: list[dict], feature_names: list[str], top_n: int = 15, custom_categories: dict = None):
    keywords = dict(UNIVERSAL_PROBLEM_CATEGORIES)
    if custom_categories:
        keywords.update(custom_categories)

    negative_reviews = [p for p in predictions if p.get("sentiment") == "negative"]

    if not negative_reviews:
        return {
            "problems": [],
            "problem_count": 0,
            "total_negative": 0,
            "top_complaint_words": [],
            "negative_review_sample": [],
        }

    def _clean_for_freq(text: str) -> str:
        text = text.lower()
        # Preserve underscores for compound negation tokens (e.g. not_working)
        text = re.sub(r"[^\w\s'_]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    # Words that, when they directly precede a complaint keyword, negate it
    # (e.g. "battery is NOT the problem"). Prevents false category attribution.
    _NEGATORS = {
        "not", "no", "never", "dont", "doesnt", "didnt", "isnt", "arent",
        "wasnt", "werent", "wont", "cant", "without", "rather than", "except",
    }

    def _is_negated(text_lower: str, keyword: str) -> bool:
        """True if a (single-word) keyword occurrence is directly negated."""
        idx = 0
        while True:
            idx = text_lower.find(keyword, idx)
            if idx == -1:
                return False
            # look back up to ~30 chars before the keyword for a negator
            tail = text_lower[max(0, idx - 30):idx].strip().rstrip()
            for neg in _NEGATORS:
                if tail.endswith(neg):
                    return True
                if not neg[-1:].isalnum() and (neg + " ") in tail:
                    return True
            idx += len(keyword)

    # Multi-word keywords that ALREADY carry negative meaning encoded in the
    # phrase itself (e.g. "not working", "poor quality", "waste of money").
    # These must not be skipped even if a standalone negator appears nearby.
    _SELF_NEGATED = {
        kw for kws in keywords.values() for kw in kws
        if kw.lower().startswith(("not ", "no ", "bad", "poor", "slow",
                                  "don't", "dont ", "waste", "overpriced",
                                  "not_working")) and " " in kw
    }

    problem_scores = {}
    problem_examples = {}
    used_example_texts = set()

    # Pre-clean each review once for speed.
    prepared = []
    for review in negative_reviews:
        raw_text = str(review.get("text", ""))
        cleaned_text = str(review.get("cleaned", ""))
        text_lower = _clean_for_freq(cleaned_text + " " + raw_text)
        snippet = raw_text[:200]
        prepared.append((text_lower, snippet))

    for category, cat_keywords in keywords.items():
        score = 0
        examples = []
        for text_lower, review_snippet in prepared:
            matched = False
            for keyword in cat_keywords:
                kw_normalized = keyword.replace(" ", "_")
                kw_lower = keyword.lower()
                in_text = kw_normalized in text_lower or kw_lower in text_lower
                if not in_text:
                    continue
                # Skip single-word matches that are directly negated, unless the
                # keyword itself encodes the negation (e.g. "not working").
                if (len(kw_lower.split()) == 1 and kw_lower not in _SELF_NEGATED
                        and _is_negated(text_lower, kw_lower)):
                    continue
                score += 1
                if len(examples) < 3 and review_snippet not in used_example_texts:
                    examples.append(review_snippet)
                    used_example_texts.add(review_snippet)
                matched = True
                break

        if score > 0:
            problem_scores[category] = score
            problem_examples[category] = examples

    # Words that should never appear as "top complaint words" — they are
    # grammatical or contextual rather than a distinct complaint theme.
    _NOISE_WORDS = {
        "month", "months", "day", "days", "week", "weeks", "flipkart", "amazon",
        "actually", "though", "really", "bit", "lot", "much", "properly",
        "overall", "thing", "things", "please", "thank", "thanks", "going",
        "come", "got", "get", "make", "want", "say", "put", "take", "one",
        "two", "first", "even", "still", "also", "just", "would", "could",
    }

    top_tfidf_words = []
    if len(negative_reviews) > 0:
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words("english"))
        stop_words.update({
            "this", "that", "with", "from", "have", "been", "were", "they",
            "their", "would", "could", "should", "about", "also", "just",
            "only", "very", "really", "much", "more", "than", "some", "into",
            "like", "when", "what", "which", "there", "then", "them", "each",
            "made", "make", "thing", "things", "one", "two", "get", "got",
            "back", "even", "still", "after", "before", "being", "over",
            "such", "through", "first", "last", "long", "little", "own",
            "other", "old", "right", "big", "high", "small", "large", "next",
            "early", "young", "important", "same", "able", "every", "found",
            "look", "day", "would", "really", "the", "and", "for", "are", "was",
        })
        complaint_stop = stop_words | _NOISE_WORDS
        complaint_stop -= {"not", "no", "never", "don", "didn", "won",
                           "wouldn", "couldn", "shouldn", "isn", "aren", "wasn", "weren"}

        neg_words = Counter()
        for review in negative_reviews:
            raw_text = review.get("text", "")
            cleaned_content = review.get("cleaned", "")
            combined = _clean_for_freq(cleaned_content + " " + raw_text)
            for word in combined.split():
                if ("_" in word or (len(word) > 3 and word not in complaint_stop and word.isalpha())) and word not in _NOISE_WORDS:
                    neg_words[word] += 1
        top_tfidf_words = [{"word": w, "count": c} for w, c in neg_words.most_common(top_n)]

    sorted_problems = sorted(problem_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    total_neg_count = max(len(negative_reviews), 1)
    MIN_PERCENTAGE = 3.0  # only show categories that affect at least 3% of negative reviews
    for category, score in sorted_problems:
        pct = round(score / total_neg_count * 100, 1)
        if pct < MIN_PERCENTAGE:
            continue
        severity = "high" if pct >= 30 else "medium" if pct >= 10 else "low"
        is_custom = bool(custom_categories and category in custom_categories)
        results.append({
            "category": category.replace("_", " ").title(),
            "category_key": category,
            "frequency": score,
            "severity": severity,
            "percentage": pct,
            "examples": problem_examples.get(category, []),
            "is_custom": is_custom,
        })

    return {
        "problems": results[:top_n],
        "problem_count": len(results),
        "total_negative": len(negative_reviews),
        "top_complaint_words": top_tfidf_words,
        "negative_review_sample": [p.get("text", "")[:300] for p in negative_reviews[:10]],
    }