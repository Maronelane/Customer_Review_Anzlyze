import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface Problem {
  category: string;
  category_key: string;
  frequency: number;
  severity: string;
  percentage: number;
  examples: string[];
}

interface Props {
  problems: Problem[];
  topWords: { word: string; count: number }[];
}

const SEVERITY_COLORS: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#6b7280",
};

const SEVERITY_BG: Record<string, string> = {
  high: "rgba(239,68,68,0.08)",
  medium: "rgba(245,158,11,0.08)",
  low: "rgba(107,114,128,0.08)",
};

export default function ProblemList({ problems, topWords }: Props) {
  const chartData = problems.slice(0, 8).map((p) => ({
    name: p.category,
    count: p.frequency,
    severity: p.severity,
  }));

  const maxWordCount = Math.max(...topWords.map((w) => w.count), 1);

  return (
    <>
      {problems.length === 0 ? (
        <div className="no-problems">
          <p>No significant problems detected. Reviews are mostly positive!</p>
        </div>
      ) : (
        <>
          <div className="chart-area">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" stroke="var(--text-muted)" fontSize={11} />
                <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 12, fill: "var(--text)" }} />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    fontSize: "13px",
                  }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]}>
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={SEVERITY_COLORS[entry.severity]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="problem-list">
            {problems.map((p) => (
              <div
                key={p.category_key}
                className={`problem-item severity-${p.severity}`}
                style={{ backgroundColor: SEVERITY_BG[p.severity] }}
              >
                <div className="problem-header">
                  <span className="problem-name">{p.category}</span>
                  <div className="problem-meta">
                    <span className={`severity-badge ${p.severity}`}>{p.severity}</span>
                    <span className="problem-pct">{p.percentage}%</span>
                    <span className="problem-freq">{p.frequency} reviews</span>
                  </div>
                </div>
                {p.examples.length > 0 && (
                  <div className="problem-examples">
                    {p.examples.slice(0, 2).map((ex, i) => (
                      <p key={i} className="example-text">
                        &ldquo;{ex.slice(0, 150)}&rdquo;
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {topWords.length > 0 && (
        <div className="top-words">
          <div className="top-words-header">
            <h4>Top Complaint Keywords</h4>
            <span className="top-words-count">{topWords.length} keywords</span>
          </div>
          <p className="top-words-explanation">
            These keywords are extracted from <strong>negative reviews only</strong>. Words are counted across both original and cleaned review text, with common stop words removed. Higher counts indicate words that appear most frequently in customer complaints.
          </p>
          <div className="top-words-list">
            {topWords.slice(0, 20).map((w, idx) => {
              const barWidth = (w.count / maxWordCount) * 100;
              return (
                <div key={w.word} className="complaint-word-row">
                  <span className="complaint-word-rank">{idx + 1}</span>
                  <span className="complaint-word-name">{w.word}</span>
                  <div className="complaint-word-bar-bg">
                    <div
                      className="complaint-word-bar"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <span className="complaint-word-count">{w.count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
