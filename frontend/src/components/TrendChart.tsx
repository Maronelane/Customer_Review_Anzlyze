import { useState, useEffect } from "react";
import { getTrend, type TrendPoint } from "../api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

interface Props {
  analysisId: string;
}

export default function TrendChart({ analysisId }: Props) {
  const [data, setData] = useState<TrendPoint[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getTrend(analysisId)
      .then((res) => {
        if (res.message) {
          setMessage(res.message);
        } else {
          setData(res.trend);
        }
      })
      .catch(() => setMessage("No date data available"));
  }, [analysisId]);

  if (message) {
    return (
      <div className="insight-card">
        <h3>Sentiment Trend</h3>
        <p className="insight-empty">{message}</p>
      </div>
    );
  }

  if (data.length === 0) return null;

  return (
    <div className="insight-card">
      <h3>Sentiment Trend Over Time</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} />
          <YAxis stroke="var(--text-muted)" fontSize={12} />
          <Tooltip
            contentStyle={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
            }}
          />
          <Legend />
          <Line type="monotone" dataKey="positive" stroke="#22c55e" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="negative" stroke="#ef4444" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="neutral" stroke="#f59e0b" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
