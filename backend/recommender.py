"""
Business Recommender: Generates actionable business suggestions based on detected problems.
"""

RECOMMENDATION_TEMPLATES = {
    "build_quality": {
        "title": "Enhance Product Quality & Durability",
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
    "performance_and_reliability": {
        "title": "Improve Performance & Reliability",
        "priority": "high",
        "suggestions": [
            "Optimize software code and resource management to reduce lag and freezing.",
            "Establish automated stress-testing pipelines prior to deployment.",
            "Address battery drain and charging issues through hardware/firmware audits.",
            "Provide clear troubleshooting guides for common error states.",
        ],
        "impact": "Reliability and stable performance directly correlate with user satisfaction.",
    },
    "usability_and_experience": {
        "title": "Simplify User Experience",
        "priority": "medium",
        "suggestions": [
            "Conduct UX testing sessions to identify confusing workflows.",
            "Simplify navigation, onboarding flows, and account management.",
            "Improve error messages and provide clear guidance for recovery.",
            "Optimize the mobile experience for on-the-go users.",
        ],
        "impact": "A smooth user experience reduces friction and increases conversions.",
    },
    "customer_service": {
        "title": "Upgrade Customer Support",
        "priority": "high",
        "suggestions": [
            "Reduce response times by implementing live chat or chatbot support.",
            "Train support staff on empathy, product knowledge, and conflict resolution.",
            "Create a comprehensive FAQ and self-service knowledge base.",
            "Implement a ticketing system to track and prioritize unresolved issues.",
        ],
        "impact": "Great service recovery can turn unhappy customers into brand advocates.",
    },
    "shipping_and_packaging": {
        "title": "Improve Delivery & Shipping Logistics",
        "priority": "high",
        "suggestions": [
            "Partner with more reliable shipping carriers to reduce delivery delays.",
            "Implement real-time tracking notifications to keep customers informed.",
            "Offer expedited shipping options for time-sensitive orders.",
            "Review and optimize warehouse packaging standards to prevent transit damage.",
        ],
        "impact": "Fast, reliable delivery directly impacts customer satisfaction and repeat purchases.",
    },
    "pricing_and_value": {
        "title": "Optimize Pricing Strategy",
        "priority": "medium",
        "suggestions": [
            "Conduct competitor pricing analysis to ensure market competitiveness.",
            "Introduce tiered pricing or bundle offers to improve perceived value.",
            "Clearly communicate the value proposition and unique features.",
            "Offer loyalty discounts or seasonal promotions to retain price-sensitive customers.",
        ],
        "impact": "Perceived value matters more than absolute price — communicate benefits clearly.",
    },
    "product_accuracy": {
        "title": "Improve Product Accuracy & Descriptions",
        "priority": "medium",
        "suggestions": [
            "Ensure product photos and descriptions accurately represent the item.",
            "Add detailed sizing charts and comparison guides.",
            "Implement barcode/QR verification during order fulfillment to stop wrong-item shipments.",
        ],
        "impact": "Accurate expectations reduce returns and increase customer trust.",
    },
    "functional_issues": {
        "title": "Address Core Functional Failures",
        "priority": "high",
        "suggestions": [
            "Investigate recurring feature, audio, or component failures.",
            "Deploy targeted patches or hardware fixes for faulty elements.",
            "Gather post-purchase feedback to detect component drop-offs early.",
        ],
        "impact": "Fixing core bugs stops major negative review spikes.",
    },
    "food_taste": {
        "title": "Improve Food Quality & Taste",
        "priority": "high",
        "suggestions": [
            "Review recipes and ingredient sourcing for consistency.",
            "Conduct blind taste tests with target customer segments.",
            "Ensure freshness through better storage and faster turnover.",
        ],
        "impact": "Taste is the primary factor in food repurchase decisions.",
    },
    "comfort": {
        "title": "Improve Comfort & Fit",
        "priority": "medium",
        "suggestions": [
            "Expand size ranges and provide detailed fit guides.",
            "Use customer reviews to refine sizing across products.",
            "Source hypoallergenic and skin-friendly materials.",
        ],
        "impact": "Comfort directly affects whether customers buy again.",
    }
}


def generate_recommendations(problems: list[dict], sentiment_distribution: dict):
    total = sentiment_distribution.get("total", 1)
    negative_pct = sentiment_distribution.get("negative", 0) / max(total, 1) * 100

    recommendations = []

    for problem in problems:
        key = problem.get("category_key")
        if key in RECOMMENDATION_TEMPLATES:
            template = RECOMMENDATION_TEMPLATES[key]
            adjusted_priority = template["priority"]
            if problem.get("severity") == "high" and negative_pct > 30:
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
        else:
            adjusted_priority = problem.get("severity", "medium")
            if problem.get("severity") == "high" and negative_pct > 30:
                adjusted_priority = "critical"

            recommendations.append({
                "title": f"Address: {problem['category']}",
                "priority": adjusted_priority,
                "problem_category": problem["category"],
                "problem_frequency": problem["frequency"],
                "problem_percentage": problem["percentage"],
                "suggestions": [
                    f"Investigate customer complaints related to '{problem['category']}'.",
                    f"Review {problem['frequency']} mentions across negative reviews for common themes.",
                    "Gather more detailed feedback on this issue from affected customers.",
                ],
                "impact": f"Addressing '{problem['category']}' concerns can improve overall customer satisfaction.",
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
    lines = ["Executive Review & Strategic Action Summary:", ""]

    if negative_pct > 40:
        lines.append("WARNING: High negative feedback concentration detected. Immediate workflow optimizations recommended.")
    elif negative_pct > 20:
        lines.append("CAUTION: Notable friction patterns identified. Target primary category templates promptly.")
    else:
        lines.append("Operational sentiment patterns remain stable. Maintain standardized template practices and monitor edge concerns.")

    if recommendations:
        top = recommendations[0]
        lines.append(f"\nPrimary Focus Template: {top['title']} — addressing structural bottlenecks affecting {top['problem_percentage']}% of monitored negative logs.")

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