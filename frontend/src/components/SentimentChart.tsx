import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

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

const COLORS = {
  positive: "#22c55e",
  negative: "#ef4444",
  neutral: "#f59e0b",
};

export default function SentimentChart({ distribution, bestModel, bestAccuracy }: Props) {
  const data = [
    { name: "Positive", value: distribution.positive },
    { name: "Negative", value: distribution.negative },
    { name: "Neutral", value: distribution.neutral },
  ].filter((d) => d.value > 0);

  const pct = (n: number) => distribution.total ? ((n / distribution.total) * 100).toFixed(1) : "0";

  return (
    <div className="card sentiment-chart-card">
      <div className="card-header">
        <h3>Sentiment Distribution</h3>
        <div className="model-badge">
          <span className="model-name">{bestModel.replace("_", " ")}</span>
          <span className="model-acc">{(bestAccuracy * 100).toFixed(1)}% acc</span>
        </div>
      </div>

      <div className="chart-area">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={3}
              dataKey="value"
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name.toLowerCase() as keyof typeof COLORS]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => [
                `${value} (${pct(value)}%)`,
                name,
              ]}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="sentiment-stats">
        <div className="stat positive">
          <span className="stat-value">{distribution.positive}</span>
          <span className="stat-label">Positive ({pct(distribution.positive)}%)</span>
        </div>
        <div className="stat negative">
          <span className="stat-value">{distribution.negative}</span>
          <span className="stat-label">Negative ({pct(distribution.negative)}%)</span>
        </div>
        <div className="stat neutral">
          <span className="stat-value">{distribution.neutral}</span>
          <span className="stat-label">Neutral ({pct(distribution.neutral)}%)</span>
        </div>
      </div>
    </div>
  );
}
