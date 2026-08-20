import re
from collections import Counter

# Universal & Electronics Problem Categories tailored for real-world reviews
UNIVERSAL_PROBLEM_CATEGORIES = {
    # --- Quality & Craftsmanship ---
    "build_quality": [
        "quality", "cheap", "flimsy", "poor", "bad", "terrible", "shoddy", 
        "weak", "fragile", "subpar", "inferior", "rubbish", "trash", "broken", 
        "broke", "defective", "damage", "fell apart", "cheaply made"
    ],
    
    # --- Performance & Reliability ---
    "performance_and_reliability": [
        "slow", "lagging", "sluggish", "performance", "unresponsive", "freezing", 
        "glitch", "freeze", "crash", "error", "bug", "stopped", "fails", 
        "not_working", "does_not_work", "stopped working", "rebooting",
        "battery", "charge", "charging", "drain", "dies", "dead", "overheat"
    ],
    
    # --- Usability & Experience ---
    "usability_and_experience": [
        "difficult", "hard", "complicated", "confusing", "unintuitive", 
        "complex", "annoying", "pain", "uncomfortable", "awkward"
    ],
    
    # --- Customer Service & Support ---
    "customer_service": [
        "service", "support", "staff", "customer", "rude", "unhelpful", 
        "agent", "representative", "response", "ignored", "contact", "manager"
    ],
    
    # --- Shipping, Delivery & Packaging ---
    "shipping_and_packaging": [
        "delivery", "shipping", "late", "slow", "delayed", "package", "arrived", 
        "courier", "track", "lost", "box", "crushed", "packing", "seal"
    ],
    
    # --- Pricing & Value ---
    "pricing_and_value": [
        "price", "expensive", "overpriced", "cost", "value", "waste", "money", 
        "rip off", "not_worth", "overcharged", "waste of money"
    ],
    
    # --- Product Accuracy & Description ---
    "product_accuracy": [
        "missing", "wrong", "different", "description", "expected", "fake", 
        "counterfeit", "not as pictured", "misleading", "inauthentic", "item", "sent"
    ],
    
    # --- Core Functionality / Feature Failures ---
    "functional_issues": [
        "feature", "option", "setting", "fail", "missing feature", "limited", 
        "restricted", "unable", "cant", "can_not", "will_not", "fails to",
        "sound", "audio", "mic", "microphone", "volume", "connection", "bluetooth"
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

    problem_scores = {}
    problem_examples = {}
    used_example_texts = set()

    for category, cat_keywords in keywords.items():
        score = 0
        examples = []
        for review in negative_reviews:
            raw_text = review.get("text", "")
            cleaned_text = review.get("cleaned", "")
            # Keep underscores intact during frequency cleanup
            text_lower = _clean_for_freq(cleaned_text + " " + raw_text)
            review_snippet = raw_text[:200]
            
            matched = False
            for keyword in cat_keywords:
                # Normalize spaces in keywords to underscores if applicable
                kw_normalized = keyword.replace(" ", "_")
                if kw_normalized in text_lower or keyword in text_lower:
                    score += 1
                    if len(examples) < 3 and review_snippet not in used_example_texts:
                        examples.append(review_snippet)
                        used_example_texts.add(review_snippet)
                    matched = True
                    break 
                    
        if score > 0:
            problem_scores[category] = score
            problem_examples[category] = examples

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
            "such", "through", "good", "well", "first", "last", "long",
            "great", "little", "own", "other", "old", "right", "big", "high",
            "small", "large", "next", "early", "young", "important", "few",
            "public", "bad", "same", "able", "every", "found", "look", "day",
        })
        complaint_stop = stop_words - {"not", "no", "never", "don", "didn",
                                       "won", "wouldn", "couldn", "shouldn", "isn", "aren", "wasn", "weren"}

        neg_words = Counter()
        for review in negative_reviews:
            raw_text = review.get("text", "")
            cleaned_content = review.get("cleaned", "")
            combined = _clean_for_freq(cleaned_content + " " + raw_text)
            for word in combined.split():
                if "_" in word or (len(word) > 3 and word not in complaint_stop and word.isalpha()):
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