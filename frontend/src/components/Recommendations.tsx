interface Recommendation {
  title: string;
  priority: string;
  problem_category: string;
  problem_frequency: number;
  problem_percentage: number;
  suggestions: string[];
  impact: string;
  examples: string[];
}

interface Props {
  recommendations: Recommendation[];
  summary: string;
}

const PRIORITY_STYLES: Record<string, { bg: string; border: string; label: string }> = {
  critical: { bg: "#fef2f2", border: "#ef4444", label: "CRITICAL" },
  high: { bg: "#fff7ed", border: "#f97316", label: "HIGH" },
  medium: { bg: "#fefce8", border: "#eab308", label: "MEDIUM" },
  low: { bg: "#f0fdf4", border: "#22c55e", label: "LOW" },
};

export default function Recommendations({ recommendations, summary }: Props) {
  const priorityCounts = recommendations.reduce(
    (acc, rec) => {
      acc[rec.priority] = (acc[rec.priority] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <>
      {recommendations.length > 0 && (
        <div className="rec-overview">
          <h4>Priority Overview</h4>
          <div className="rec-overview-grid">
            {(["critical", "high", "medium", "low"] as const).map((level) => {
              const count = priorityCounts[level] || 0;
              if (count === 0) return null;
              const style = PRIORITY_STYLES[level];
              return (
                <div key={level} className="rec-overview-item" style={{ borderColor: style.border }}>
                  <span className="rec-overview-count" style={{ color: style.border }}>{count}</span>
                  <span className="rec-overview-label">{style.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {recommendations.length === 0 ? (
        <div className="no-recommendations">
          <p>No specific recommendations. Consider monitoring reviews over time.</p>
        </div>
      ) : (
        <div className="recommendation-list">
          {recommendations.map((rec, i) => {
            const style = PRIORITY_STYLES[rec.priority] || PRIORITY_STYLES.medium;
            return (
              <div
                key={i}
                className="recommendation-item"
                style={{ borderLeftColor: style.border }}
              >
                <div className="rec-header">
                  <span
                    className="priority-badge"
                    style={{ backgroundColor: style.bg, color: style.border, border: `1px solid ${style.border}` }}
                  >
                    {style.label}
                  </span>
                  <h4>{rec.title}</h4>
                </div>

                <p className="rec-impact">{rec.impact}</p>

                <div className="rec-meta">
                  <span>Affects {rec.problem_percentage}% of negative reviews</span>
                  <span>{rec.problem_frequency} mentions</span>
                </div>

                <ul className="suggestions-list">
                  {rec.suggestions.map((s, j) => (
                    <li key={j}>{s}</li>
                  ))}
                </ul>

                {rec.examples.length > 0 && (
                  <div className="rec-examples">
                    <h5>Sample Complaints</h5>
                    {rec.examples.map((ex, j) => (
                      <p key={j} className="example-quote">"{ex.slice(0, 150)}..."</p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
