interface Props {
  distribution: {
    positive: number;
    negative: number;
    neutral: number;
    total: number;
  };
  bestModel: string;
  bestAccuracy: number;
}

const SENTIMENTS = [
  { key: "positive", label: "Positive", color: "var(--positive)", icon: "+" },
  { key: "negative", label: "Negative", color: "var(--negative)", icon: "-" },
  { key: "neutral", label: "Neutral", color: "var(--neutral)", icon: "~" },
] as const;

export default function SentimentChart({ distribution, bestModel, bestAccuracy }: Props) {
  const total = distribution.total || 1;
  const pct = (n: number) => ((n / total) * 100).toFixed(1);

  return (
    <div className="card sentiment-card">
      <div className="card-header">
        <h3>Sentiment Distribution</h3>
        <div className="model-badge">
          <span className="model-name">{bestModel.replace("_", " ")}</span>
          <span className="model-acc">{(bestAccuracy * 100).toFixed(1)}% acc</span>
        </div>
      </div>

      <div className="sentiment-donut-wrapper">
        <svg viewBox="0 0 120 120" className="sentiment-donut">
          {(() => {
            const radius = 45;
            const circumference = 2 * Math.PI * radius;
            let offset = 0;
            const items = SENTIMENTS.map((s) => ({
              ...s,
              value: distribution[s.key as keyof typeof distribution] as number,
            })).filter((s) => s.value > 0);

            return items.map((s) => {
              const pctVal = s.value / total;
              const dashLen = pctVal * circumference;
              const dashOffset = -offset * circumference;
              offset += pctVal;
              return (
                <circle
                  key={s.key}
                  cx="60"
                  cy="60"
                  r={radius}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="16"
                  strokeDasharray={`${dashLen} ${circumference - dashLen}`}
                  strokeDashoffset={dashOffset}
                  strokeLinecap="round"
                  className="donut-segment"
                />
              );
            });
          })()}
          <text x="60" y="56" textAnchor="middle" className="donut-total">
            {total.toLocaleString()}
          </text>
          <text x="60" y="72" textAnchor="middle" className="donut-label">
            reviews
          </text>
        </svg>
      </div>

      <div className="sentiment-bars">
        {SENTIMENTS.map((s) => {
          const val = distribution[s.key as keyof typeof distribution] as number;
          const pctVal = (val / total) * 100;
          return (
            <div key={s.key} className="sentiment-bar-row">
              <div className="bar-row-header">
                <span className="bar-label">{s.label}</span>
                <span className="bar-count">
                  {val.toLocaleString()} <span className="bar-pct">({pct(val)}%)</span>
                </span>
              </div>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{
                    width: `${pctVal}%`,
                    backgroundColor: s.color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="sentiment-verdict">
        {posPct(distribution) > 60
          ? "Overall sentiment is strongly positive."
          : negPct(distribution) > 40
          ? "Significant negative sentiment — action recommended."
          : "Mixed sentiment across reviews."}
      </div>
    </div>
  );
}

function posPct(d: { positive: number; total: number }) {
  return d.total ? (d.positive / d.total) * 100 : 0;
}

function negPct(d: { negative: number; total: number }) {
  return d.total ? (d.negative / d.total) * 100 : 0;
}
