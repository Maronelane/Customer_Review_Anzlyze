"""
Business Recommender: Generates data-driven, dynamic business recommendations
based on actual customer review content, complaint patterns, and sentiment data.
"""

import re
from collections import Counter


CATEGORY_LABELS = {
    "build_quality": "Product Quality & Durability",
    "performance_and_reliability": "Performance & Reliability",
    "usability_and_experience": "User Experience & Usability",
    "customer_service": "Customer Service & Support",
    "shipping_and_packaging": "Delivery & Packaging",
    "pricing_and_value": "Pricing & Value for Money",
    "product_accuracy": "Product Accuracy & Descriptions",
    "functional_issues": "Core Functionality & Features",
    "food_taste": "Food Quality & Taste",
    "comfort": "Comfort & Fit",
}

CATEGORY_ACTION_VERBS = {
    "build_quality": "improve build quality and material durability",
    "performance_and_reliability": "resolve performance and reliability issues",
    "usability_and_experience": "simplify the user experience",
    "customer_service": "enhance customer support responsiveness",
    "shipping_and_packaging": "improve delivery speed and packaging quality",
    "pricing_and_value": "realign pricing with perceived value",
    "product_accuracy": "ensure product descriptions match reality",
    "functional_issues": "fix core feature and functionality failures",
    "food_taste": "improve food taste and ingredient quality",
    "comfort": "improve product comfort and sizing accuracy",
}


def _extract_themes(examples: list[str], top_words: list[dict]) -> list[str]:
    """Extract key complaint themes from example reviews and top complaint words."""
    word_set = {w["word"] for w in top_words[:20]}
    themes = []

    for ex in examples:
        words = re.findall(r"\b\w+\b", ex.lower())
        meaningful = [w for w in words if w in word_set and len(w) > 3]
        themes.extend(meaningful[:3])

    theme_counts = Counter(themes)
    return [t for t, _ in theme_counts.most_common(5)]


def _generate_suggestions(category: str, problem: dict, top_words: list[dict],
                          sentiment_dist: dict, all_problems: list[dict]) -> list[str]:
    """Generate dynamic suggestions based on actual complaint data."""
    freq = problem.get("frequency", 0)
    pct = problem.get("percentage", 0)
    severity = problem.get("severity", "medium")
    examples = problem.get("examples", [])
    themes = _extract_themes(examples, top_words)

    total = sentiment_dist.get("total", 1)
    neg_count = sentiment_dist.get("negative", 0)
    neg_pct = round(neg_count / max(total, 1) * 100, 1)
    pos_count = sentiment_dist.get("positive", 0)
    pos_pct = round(pos_count / max(total, 1) * 100, 1)

    other_categories = [p["category"] for p in all_problems if p["category_key"] != category][:3]
    other_str = ", ".join(other_categories) if other_categories else "none"

    action = CATEGORY_ACTION_VERBS.get(category, f"address {category.replace('_', ' ')} concerns")

    suggestions = []

    if themes:
        theme_str = ", ".join(themes[:3])
        suggestions.append(
            f"Customers specifically mention issues with: {theme_str}. "
            f"Prioritize fixing these {freq} reported complaints ({pct}% of negative reviews)."
        )
    else:
        suggestions.append(
            f"Review and address the {freq} customer complaints in this category "
            f"({pct}% of negative feedback)."
        )

    if severity == "high":
        suggestions.append(
            f"This is a HIGH-severity issue affecting over 30% of dissatisfied customers. "
            f"Immediate action recommended — {action}."
        )
    elif severity == "medium":
        suggestions.append(
            f"This issue appears in {pct}% of negative reviews. "
            f"Schedule a focused review to {action}."
        )
    else:
        suggestions.append(
            f"Lower-priority concern ({pct}% of negative reviews). "
            f"Monitor for escalation and {action} when resources allow."
        )

    if examples:
        snippet = examples[0][:120].strip()
        if snippet:
            suggestions.append(
                f"Representative complaint: \"{snippet}...\" — "
                f"use this to understand the root cause."
            )

    related = [p for p in all_problems
               if p["category_key"] != category and p.get("severity") in ("high", "medium")]
    if related:
        related_names = [p["category"] for p in related[:2]]
        suggestions.append(
            f"This issue overlaps with: {', '.join(related_names)}. "
            f"Consider a unified fix to address multiple pain points at once."
        )

    return suggestions[:5]


def _generate_impact(category: str, problem: dict, sentiment_dist: dict) -> str:
    """Generate a data-driven impact statement."""
    freq = problem.get("frequency", 0)
    pct = problem.get("percentage", 0)
    severity = problem.get("severity", "medium")

    total = sentiment_dist.get("total", 1)
    neg_count = sentiment_dist.get("negative", 0)
    pos_count = sentiment_dist.get("positive", 0)
    neg_pct = round(neg_count / max(total, 1) * 100, 1)

    if severity == "high":
        return (
            f"Critical: {pct}% of unhappy customers report {category.replace('_', ' ')} issues. "
            f"Resolving this could shift up to {pct}% of negative sentiment toward positive."
        )
    elif severity == "medium":
        recovery_potential = min(pct, round(100 - neg_pct, 1))
        return (
            f"{pct}% of negative reviews cite this. "
            f"Improvements here could recover approximately {recovery_potential}% of at-risk sentiment."
        )
    else:
        return (
            f"Affects {pct}% of negative reviews ({freq} mentions). "
            f"Lower urgency but contributes to overall dissatisfaction."
        )


def _generate_title(category: str, problem: dict) -> str:
    """Generate a specific title based on category and data."""
    base = CATEGORY_LABELS.get(category, category.replace("_", " ").title())
    freq = problem.get("frequency", 0)
    severity = problem.get("severity", "medium")

    if severity == "high":
        return f"Urgent: Fix {base} ({freq} complaints)"
    elif severity == "medium":
        return f"Improve {base} ({freq} mentions)"
    else:
        return f"Monitor {base} ({freq} mentions)"


def generate_recommendations(problems: list[dict], sentiment_distribution: dict,
                             top_complaint_words: list[dict] = None,
                             negative_review_sample: list[str] = None):
    """Generate dynamic, data-driven business recommendations."""
    total = sentiment_distribution.get("total", 1)
    negative_pct = sentiment_distribution.get("negative", 0) / max(total, 1) * 100

    if top_complaint_words is None:
        top_complaint_words = []
    if negative_review_sample is None:
        negative_review_sample = []

    recommendations = []

    for problem in problems:
        key = problem.get("category_key")
        adjusted_priority = problem.get("severity", "medium")
        if problem.get("severity") == "high" and negative_pct > 30:
            adjusted_priority = "critical"

        suggestions = _generate_suggestions(
            key, problem, top_complaint_words, sentiment_distribution, problems
        )
        impact = _generate_impact(key, problem, sentiment_distribution)
        title = _generate_title(key, problem)

        recommendations.append({
            "title": title,
            "priority": adjusted_priority,
            "problem_category": problem["category"],
            "problem_frequency": problem["frequency"],
            "problem_percentage": problem["percentage"],
            "suggestions": suggestions,
            "impact": impact,
            "examples": problem.get("examples", []),
        })

    recommendations.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["priority"], 4))
    summary = _generate_summary(recommendations, sentiment_distribution, negative_pct)

    return {
        "recommendations": recommendations,
        "summary": summary,
        "overall_sentiment": _get_sentiment_label(negative_pct, sentiment_distribution),
        "total_recommendations": len(recommendations),
    }


def _generate_summary(recommendations: list[dict], dist: dict, negative_pct: float) -> str:
    total = dist.get("total", 1)
    pos = dist.get("positive", 0)
    neg = dist.get("negative", 0)
    neu = dist.get("neutral", 0)
    pos_pct = round(pos / max(total, 1) * 100, 1)
    neg_pct = round(neg / max(total, 1) * 100, 1)

    lines = ["Executive Review & Strategic Action Summary:", ""]

    lines.append(
        f"Analyzed {total} customer reviews: {pos_pct}% positive, "
        f"{neg_pct}% negative, {round(neu / max(total, 1) * 100, 1)}% neutral."
    )

    if negative_pct > 40:
        lines.append(
            "\nWARNING: High negative feedback concentration. "
            "Immediate action required on the top issues below."
        )
    elif negative_pct > 20:
        lines.append(
            "\nCAUTION: Notable negative patterns detected. "
            "Focus on the high-priority categories to prevent further sentiment decline."
        )
    else:
        lines.append(
            "\nOverall sentiment is stable. "
            "Monitor the flagged areas and continue maintaining current quality standards."
        )

    if recommendations:
        top = recommendations[0]
        lines.append(
            f"\nPrimary Focus: {top['title']} — "
            f"affects {top['problem_percentage']}% of negative reviews "
            f"({top['problem_frequency']} mentions)."
        )

        if len(recommendations) > 1:
            cats = [r["problem_category"] for r in recommendations[:3]]
            lines.append(f"Top problem areas: {', '.join(cats)}.")

    return "\n".join(lines)


def _get_sentiment_label(negative_pct: float, dist: dict) -> str:
    total = dist.get("total", 1)
    pos_pct = dist.get("positive", 0) / total * 100
    if negative_pct > 40:
        return "critical"
    elif negative_pct > 25:
        return "needs_attention"
    elif pos_pct > 60:
        return "positive"
    return "mixed"
