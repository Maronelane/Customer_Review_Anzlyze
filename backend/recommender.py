"""
Business Recommender: Generates actionable business suggestions based on detected problems.
"""

RECOMMENDATION_TEMPLATES = {
    "delivery": {
        "title": "Improve Delivery & Shipping",
        "priority": "high",
        "suggestions": [
            "Partner with more reliable shipping carriers to reduce delivery delays.",
            "Implement real-time tracking notifications to keep customers informed.",
            "Offer expedited shipping options for time-sensitive orders.",
            "Review and optimize warehouse logistics to speed up order processing.",
            "Set clear delivery expectations on product pages to reduce complaints.",
        ],
        "impact": "Fast, reliable delivery directly impacts customer satisfaction and repeat purchases.",
    },
    "quality": {
        "title": "Enhance Product Quality",
        "priority": "high",
        "suggestions": [
            "Implement stricter quality control checks before shipping.",
            "Source higher-quality materials from vetted suppliers.",
            "Offer hassle-free replacements or refunds for defective items.",
            "Conduct regular product testing and durability assessments.",
            "Create a quality feedback loop between customers and the product team.",
        ],
        "impact": "Product quality is the #1 driver of customer trust and long-term loyalty.",
    },
    "price": {
        "title": "Optimize Pricing Strategy",
        "priority": "medium",
        "suggestions": [
            "Conduct competitor pricing analysis to ensure market competitiveness.",
            "Introduce tiered pricing or bundle offers to improve perceived value.",
            "Clearly communicate the value proposition and unique features.",
            "Offer loyalty discounts or seasonal promotions to retain price-sensitive customers.",
            "Consider a money-back guarantee to reduce perceived purchase risk.",
        ],
        "impact": "Perceived value matters more than absolute price — communicate benefits clearly.",
    },
    "customer_service": {
        "title": "Upgrade Customer Support",
        "priority": "high",
        "suggestions": [
            "Reduce response times by implementing live chat or chatbot support.",
            "Train support staff on empathy, product knowledge, and conflict resolution.",
            "Create a comprehensive FAQ and self-service knowledge base.",
            "Implement a ticketing system to track and prioritize unresolved issues.",
            "Follow up with dissatisfied customers to ensure resolution satisfaction.",
        ],
        "impact": "Great service recovery can turn unhappy customers into brand advocates.",
    },
    "product": {
        "title": "Improve Product Accuracy",
        "priority": "medium",
        "suggestions": [
            "Ensure product photos and descriptions accurately represent the item.",
            "Add detailed sizing charts and comparison guides.",
            "Implement better packaging to prevent wrong-item shipments.",
            "Use barcode/QR verification during order fulfillment.",
            "Gather post-purchase feedback to catch discrepancies early.",
        ],
        "impact": "Accurate expectations reduce returns and increase customer trust.",
    },
    "usability": {
        "title": "Simplify User Experience",
        "priority": "medium",
        "suggestions": [
            "Conduct UX testing sessions to identify pain points.",
            "Simplify the checkout and account management flows.",
            "Improve error messages and provide clear guidance for recovery.",
            "Optimize the mobile experience for on-the-go users.",
            "Add tooltips, tutorials, or onboarding guides for complex features.",
        ],
        "impact": "A smooth user experience reduces friction and increases conversions.",
    },
    "food_taste": {
        "title": "Improve Food Quality & Taste",
        "priority": "high",
        "suggestions": [
            "Review recipes and ingredient sourcing for consistency.",
            "Conduct blind taste tests with target customer segments.",
            "Ensure freshness through better storage and faster turnover.",
            "Offer sample sizes or variety packs to help customers find favorites.",
            "Highlight preparation instructions to ensure optimal taste at home.",
        ],
        "impact": "Taste is the primary factor in food repurchase decisions.",
    },
    "comfort": {
        "title": "Improve Comfort & Fit",
        "priority": "medium",
        "suggestions": [
            "Expand size ranges and provide detailed fit guides.",
            "Use customer reviews to refine sizing across products.",
            "Offer free returns/exchanges to reduce purchase hesitation.",
            "Source hypoallergenic and skin-friendly materials.",
            "Collect body measurement data to improve future designs.",
        ],
        "impact": "Comfort directly affects whether customers buy again.",
    },
}


def generate_recommendations(problems: list[dict], sentiment_distribution: dict):
    total = sentiment_distribution.get("total", 1)
    negative_pct = sentiment_distribution.get("negative", 0) / max(total, 1) * 100

    recommendations = []

    for problem in problems:
        key = problem["category_key"]
        if key in RECOMMENDATION_TEMPLATES:
            template = RECOMMENDATION_TEMPLATES[key]
            adjusted_priority = template["priority"]
            if problem["severity"] == "high" and negative_pct > 30:
                adjusted_priority = "critical"

            recommendations.append({
                "title": template["title"],
                "priority": adjusted_priority,
                "problem_category": problem["category"],
                "problem_frequency": problem["frequency"],
                "problem_percentage": problem["percentage"],
                "suggestions": template["suggestions"],
                "impact": template["impact"],
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
    total = dist.get("total", 0)
    pos = dist.get("positive", 0)
    neg = dist.get("negative", 0)
    neu = dist.get("neutral", 0)

    lines = [
        f"Analysis of {total} customer reviews revealed:",
        f"  - {pos} positive ({round(pos/max(total,1)*100, 1)}%)",
        f"  - {neg} negative ({round(neg/max(total,1)*100, 1)}%)",
        f"  - {neu} neutral ({round(neu/max(total,1)*100, 1)}%)",
        "",
    ]

    if negative_pct > 40:
        lines.append("WARNING: Negative sentiment is critically high. Immediate action recommended.")
    elif negative_pct > 20:
        lines.append("CAUTION: Significant negative sentiment detected. Address top issues promptly.")
    else:
        lines.append("Overall sentiment is healthy. Focus on maintaining quality and addressing minor issues.")

    if recommendations:
        top = recommendations[0]
        lines.append(f"\nTop priority: {top['title']} — affecting {top['problem_percentage']}% of negative reviews.")

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
