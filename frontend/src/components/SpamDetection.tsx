import { useState, useEffect } from "react";
import { getSpamSummary, type SpamData } from "../api";

interface Props {
  analysisId: string;
}

const SENTIMENT_DOT: Record<string, string> = {
  positive: "#22c55e",
  negative: "#ef4444",
  neutral: "#f59e0b",
};

export default function SpamDetection({ analysisId }: Props) {
  const [data, setData] = useState<SpamData | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    getSpamSummary(analysisId)
      .then(setData)
      .catch(() => {});
  }, [analysisId]);

  if (!data) return null;

  const { spam_summary, flagged_reviews } = data;
  const pct = spam_summary.flagged_percentage;
  const riskLevel = pct > 20 ? "high" : pct > 10 ? "medium" : "low";
  const displayed = showAll ? flagged_reviews : flagged_reviews.slice(0, 10);

  return (
    <div className="insight-card spam-card">
      <div className="spam-header">
        <h3>Fake Review / Spam Detection</h3>
        <div className={`spam-risk-badge ${riskLevel}`}>
          {riskLevel.toUpperCase()} RISK
        </div>
      </div>

      <div className="spam-stats">
        <div className="spam-stat">
          <span className="spam-stat-value">{spam_summary.total_flagged}</span>
          <span className="spam-stat-label">Flagged Reviews</span>
        </div>
        <div className="spam-stat">
          <span className="spam-stat-value">{spam_summary.total_reviews}</span>
          <span className="spam-stat-label">Total Reviews</span>
        </div>
        <div className="spam-stat">
          <span className="spam-stat-value">{pct}%</span>
          <span className="spam-stat-label">Spam Rate</span>
        </div>
      </div>

      <div className="spam-bar-container">
        <div className="spam-bar-bg">
          <div
            className="spam-bar"
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
      </div>

      {flagged_reviews.length > 0 && (
        <>
          <h4 className="spam-flagged-title">
            Flagged Reviews ({flagged_reviews.length})
          </h4>
          <div className="spam-review-list">
            {displayed.map((review, i) => (
              <div key={i} className="spam-review-item">
                <div className="spam-review-header">
                  <span
                    className="sentiment-dot"
                    style={{ backgroundColor: SENTIMENT_DOT[review.sentiment] || "#6b7280" }}
                  />
                  <span className="spam-review-sentiment">{review.sentiment}</span>
                  <span className="spam-score-badge">
                    Score: {review.spam_score.toFixed(2)}
                  </span>
                </div>
                <p className="spam-review-text">
                  {review.review_text.slice(0, 200)}
                  {review.review_text.length > 200 && "..."}
                </p>
              </div>
            ))}
          </div>
          {flagged_reviews.length > 10 && (
            <button
              className="spam-show-more"
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? "Show Less" : `Show All (${flagged_reviews.length})`}
            </button>
          )}
        </>
      )}

      {flagged_reviews.length === 0 && (
        <p className="spam-clean-msg">
          No suspicious reviews detected. All reviews appear genuine.
        </p>
      )}
    </div>
  );
}
