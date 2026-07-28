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

export default function ProblemList({ problems, topWords }: Props) {
  const chartData = problems.slice(0, 8).map((p) => ({
    name: p.category,
    count: p.frequency,
    severity: p.severity,
  }));

  return (
    <div className="card problem-card">
      <h3>Detected Problems</h3>

      {problems.length === 0 ? (
        <div className="no-problems">
          <p>No significant problems detected. Reviews are mostly positive!</p>
        </div>
      ) : (
        <>
          <div className="chart-area">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
                <Tooltip />
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
              <div key={p.category_key} className={`problem-item severity-${p.severity}`}>
                <div className="problem-header">
                  <span className="problem-name">{p.category}</span>
                  <div className="problem-meta">
                    <span className={`severity-badge ${p.severity}`}>{p.severity}</span>
                    <span className="problem-pct">{p.percentage}%</span>
                  </div>
                </div>
                {p.examples.length > 0 && (
                  <div className="problem-examples">
                    {p.examples.slice(0, 2).map((ex, i) => (
                      <p key={i} className="example-text">"{ex.slice(0, 120)}..."</p>
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
          <h4>Top Complaint Keywords</h4>
          <div className="word-cloud">
            {topWords.slice(0, 15).map((w) => (
              <span
                key={w.word}
                className="keyword-tag"
                style={{ fontSize: `${Math.min(10 + w.count * 0.5, 20)}px` }}
              >
                {w.word}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
