import { useState, useEffect } from "react";
import { getSpamSummary, type SpamData, type SpamSummary, type Prediction } from "../api";

interface Props {
  analysisId: string;
}

const SENTIMENT_COLOR: Record<string, string> = {
  positive: "#22c55e",
  negative: "#ef4444",
  neutral: "#f59e0b",
};

function getSpamReasons(review: Prediction): string[] {
  const reasons: string[] = [];
  const text = review.review_text || "";
  const len = text.trim().length;

  if (len < 10) reasons.push("Too short");
  else if (len < 25) reasons.push("Very brief");

  const words = text.toLowerCase().split(/\s+/);
  const uniqueRatio = new Set(words).size / Math.max(words.length, 1);
  if (uniqueRatio < 0.3 && words.length > 3) reasons.push("Repetitive");

  const capsRatio = (text.match(/[A-Z]/g) || []).length / Math.max(text.length, 1);
  if (capsRatio > 0.5) reasons.push("Excessive caps");

  if (/[!?]{3,}/.test(text)) reasons.push("Excessive punctuation");

  if (/https?:\/\/|www\.|\.com/i.test(text)) reasons.push("Contains URL");

  const genericPhrases = ["good product", "great product", "love it", "best product",
    "amazing", "highly recommend", "10/10", "must buy", "terrible", "worst", "do not buy"];
  const genericCount = genericPhrases.filter(p => text.toLowerCase().includes(p)).length;
  if (genericCount >= 2) reasons.push("Generic phrases");
  else if (genericCount === 1 && len < 40) reasons.push("Generic & short");

  const promoWords = ["coupon", "discount", "promo", "free shipping", "act now", "subscribe"];
  if (promoWords.some(w => text.toLowerCase().includes(w))) reasons.push("Promotional");

  if (reasons.length === 0) reasons.push("Suspicious pattern");
  return reasons;
}

export default function SpamDetection({ analysisId }: Props) {
  const [data, setData] = useState<SpamData | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSpamSummary(analysisId)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [analysisId]);

  if (loading) {
    return <div className="spam-loading">Loading spam analysis...</div>;
  }

  if (!data) return <p className="spam-empty">Spam data unavailable.</p>;

  const ss = data.spam_summary as SpamSummary | undefined;
  const flagged_reviews = data.flagged_reviews || [];
  const pct = ss?.flagged_percentage ?? 0;
  const riskLevel = pct > 20 ? "high" : pct > 10 ? "medium" : "low";
  const cleanCount = (ss?.total_reviews ?? 0) - (ss?.total_flagged ?? 0);
  const displayed = showAll ? flagged_reviews : flagged_reviews.slice(0, 8);

  const reasonCounts: Record<string, number> = {};
  (flagged_reviews || []).forEach((r) => {
    getSpamReasons(r).forEach((reason) => {
      reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
    });
  });
  const topReasons = Object.entries(reasonCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <>
      <div className="spam-overview">
        <div className="spam-donut-wrapper">
          <svg viewBox="0 0 100 100" className="spam-donut">
            <circle cx="50" cy="50" r="38" fill="none" stroke="var(--bg-hover)" strokeWidth="12" />
            <circle
              cx="50" cy="50" r="38" fill="none"
              stroke={riskLevel === "high" ? "#ef4444" : riskLevel === "medium" ? "#f59e0b" : "#22c55e"}
              strokeWidth="12"
              strokeDasharray={`${(pct / 100) * 238.76} ${238.76}`}
              strokeDashoffset="0"
              strokeLinecap="round"
              transform="rotate(-90 50 50)"
              className="donut-segment"
            />
            <text x="50" y="46" textAnchor="middle" className="donut-total">{pct}%</text>
            <text x="50" y="60" textAnchor="middle" className="donut-label">spam rate</text>
          </svg>
        </div>

        <div className="spam-numbers">
          <div className="spam-num clean">
            <span className="spam-num-val">{cleanCount.toLocaleString()}</span>
            <span className="spam-num-lbl">Clean Reviews</span>
          </div>
          <div className="spam-num flagged">
            <span className="spam-num-val">{(ss?.total_flagged ?? 0).toLocaleString()}</span>
            <span className="spam-num-lbl">Flagged</span>
          </div>
          <div className="spam-num total">
            <span className="spam-num-val">{(ss?.total_reviews ?? 0).toLocaleString()}</span>
            <span className="spam-num-lbl">Total</span>
          </div>
        </div>
      </div>

      {topReasons.length > 0 && (
        <div className="spam-reasons">
          <h4>Why Reviews Were Flagged</h4>
          <div className="reason-tags">
            {topReasons.map(([reason, count]) => (
              <span key={reason} className="reason-tag">
                {reason} <span className="reason-count">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {flagged_reviews.length > 0 && (
        <div className="spam-flagged-section">
          <button
            className="spam-collapse-toggle"
            onClick={() => setShowAll(!showAll)}
          >
            <span>Flagged Reviews ({flagged_reviews.length})</span>
            <span className={`collapse-icon ${showAll ? "open" : ""}`}>&#9662;</span>
          </button>

          {showAll && (
            <div className="spam-review-list">
              {displayed.map((review, i) => {
                const isExpanded = expanded === i;
                const reasons = getSpamReasons(review);
                return (
                  <div key={i} className={`spam-review-item ${isExpanded ? "expanded" : ""}`}>
                    <button
                      className="spam-review-clickable"
                      onClick={() => setExpanded(isExpanded ? null : i)}
                    >
                      <div className="spam-review-left">
                        <span
                          className="sentiment-dot"
                          style={{ backgroundColor: SENTIMENT_COLOR[review.sentiment] || "#6b7280" }}
                        />
                        <span className="spam-review-text-preview">
                          {review.review_text.slice(0, 100)}
                          {review.review_text.length > 100 && "..."}
                        </span>
                      </div>
                      <div className="spam-review-right">
                        <span className="spam-score-pill">{review.spam_score.toFixed(2)}</span>
                        <span className={`expand-arrow ${isExpanded ? "open" : ""}`}>&#9656;</span>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="spam-review-detail">
                        <p className="spam-full-text">{review.review_text}</p>
                        <div className="spam-review-reasons">
                          {reasons.map((r) => (
                            <span key={r} className="reason-tag small">{r}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {flagged_reviews.length === 0 && (
        <div className="spam-clean-state">
          <span className="clean-icon">&#10003;</span>
          <p>All {(ss?.total_reviews ?? 0).toLocaleString()} reviews appear genuine. No suspicious activity detected.</p>
        </div>
      )}
    </>
  );
}
