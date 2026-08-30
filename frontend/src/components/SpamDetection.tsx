import { useState, useEffect } from "react";
import { getSpamSummary, type SpamData, type SpamSummary, type Prediction } from "../api";

interface Props {
  analysisId: string;
  activeModel?: string;
}

const SENTIMENT_COLOR: Record<string, string> = {
  positive: "#22c55e",
  negative: "#ef4444",
  neutral: "#f59e0b",
};

const RISK_COLOR: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

const RISK_LABEL: Record<string, string> = {
  high: "High risk",
  medium: "Medium risk",
  low: "Low risk",
};

function fmtScore(score: number): string {
  return (score * 100).toFixed(0) + "%";
}

export default function SpamDetection({ analysisId, activeModel }: Props) {
  const [data, setData] = useState<SpamData | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSpamSummary(analysisId, activeModel)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [analysisId, activeModel]);

  if (loading) {
    return (
      <div className="spam-loading">
        <div style={{ display: 'flex', gap: 24, alignItems: 'center', padding: '12px 0' }}>
          <div className="skeleton" style={{ width: 110, height: 110, borderRadius: '50%' }} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div className="skeleton skeleton-text short" />
            <div className="skeleton skeleton-text medium" />
            <div className="skeleton skeleton-text short" />
          </div>
        </div>
      </div>
    );
  }

  if (!data) return <p className="spam-empty">Spam data unavailable.</p>;

  const ss = data.spam_summary as SpamSummary | undefined;
  const flagged_reviews = data.flagged_reviews || [];
  const pct = ss?.flagged_percentage ?? 0;
  const riskLevel = pct > 20 ? "high" : pct > 10 ? "medium" : "low";
  const cleanCount = (ss?.total_reviews ?? 0) - (ss?.total_flagged ?? 0);
  const displayed = showAll ? flagged_reviews : flagged_reviews.slice(0, 8);
  // Show small but real percentages so ~0.02% isn't rounded to a false "0%".
  const pctLabel = pct < 0.1 && pct > 0 ? pct.toFixed(2) : pct.toFixed(1);

  // Aggregate why reviews were flagged (using explainable backend signals)
  const signalCounts: Record<string, number> = {};
  (flagged_reviews || []).forEach((r) => {
    (r.spam_reasons || []).forEach((reason) => {
      signalCounts[reason.signal] = (signalCounts[reason.signal] || 0) + 1;
    });
  });
  const topSignals = Object.entries(signalCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <>
      <div className="spam-overview">
        <div className="spam-donut-wrapper">
          <svg viewBox="0 0 100 100" className="spam-donut">
            <circle cx="50" cy="50" r="38" fill="none" stroke="var(--bg-hover)" strokeWidth="12" />
            <circle
              cx="50" cy="50" r="38" fill="none"
              stroke={RISK_COLOR[riskLevel]}
              strokeWidth="12"
              strokeDasharray={`${Math.max((pct / 100) * 238.76, pct > 0 ? 2 : 0)} ${238.76}`}
              strokeDashoffset="0"
              strokeLinecap="round"
              transform="rotate(-90 50 50)"
              className="donut-segment"
            />
            <text x="50" y="46" textAnchor="middle" className="donut-total">{pctLabel}%</text>
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

      <div className="spam-score-legend">
        <h4>How scores work</h4>
        <p>
          A review is only flagged for a clear, objective reason — most commonly because
          it contains <strong>promotional content</strong> such as links, contact details,
          or "buy now" language, or because its <strong>substantive text is duplicated many
          times across the dataset</strong> (a classic copy-paste fake-review / bot pattern).
          Short or generic praise ("good", "nice") is <strong>never</strong> flagged, even
          when many different customers happen to repeat it — that's genuine crowd behaviour.
        </p>
        <div className="spam-legend-scales">
          <span className="legend-scale low">0–54% · Genuine</span>
          <span className="legend-scale medium">55–79% · Suspicious</span>
          <span className="legend-scale high">80–100% · Likely spam</span>
        </div>
      </div>

      {topSignals.length > 0 && (
        <div className="spam-reasons">
          <h4>Why Reviews Were Flagged</h4>
          <div className="reason-tags">
            {topSignals.map(([signal, count]) => (
              <span key={signal} className="reason-tag">
                {signal} <span className="reason-count">{count}</span>
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
                const reasons = review.spam_reasons || [];
                const risk = review.spam_confidence || (review.spam_score >= 0.8 ? "high" : review.spam_score >= 0.55 ? "medium" : "low");
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
                        <span
                          className={`spam-score-pill risk-${risk}`}
                          title={`${fmtScore(review.spam_score)} confidence - ${RISK_LABEL[risk]}`}
                        >
                          {fmtScore(review.spam_score)} <span className="spam-risk-dot">&#8226;</span>
                        </span>
                        <span className={`expand-arrow ${isExpanded ? "open" : ""}`}>&#9656;</span>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="spam-review-detail">
                        <p className="spam-full-text">{review.review_text}</p>
                        <div className="spam-confidence-line">
                          <strong>{fmtScore(review.spam_score)}</strong> spam confidence ·{" "}
                          <strong className={risk}>{RISK_LABEL[risk]}</strong>
                        </div>
                        <div className="spam-review-reasons">
                          {reasons.map((r, ri) => (
                            <div key={ri} className="spam-conf-reason">
                              <span className="reason-tag small">{r.signal}</span>
                              <span className="reason-detail">{r.detail}</span>
                            </div>
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
