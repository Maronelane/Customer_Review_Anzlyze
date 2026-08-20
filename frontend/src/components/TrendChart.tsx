import { useState, useEffect } from "react";
import { getTrend, type TrendPoint } from "../api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

interface Props {
  analysisId: string;
}

export default function TrendChart({ analysisId }: Props) {
  const [data, setData] = useState<TrendPoint[] | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getTrend(analysisId)
      .then((res) => {
        if (res.message) {
          setMessage(res.message);
        } else {
          setData(res.trend || []);
        }
      })
      .catch(() => setMessage("No date data available"));
  }, [analysisId]);

  if (data === null && !message) {
    return (
      <div className="trend-loading">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '12px 0' }}>
          <div className="skeleton skeleton-text wide" />
          <div className="skeleton skeleton-text wide" style={{ height: 180 }} />
          <div className="skeleton skeleton-text medium" />
        </div>
      </div>
    );
  }

  if (message) {
    return <div className="trend-empty" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ opacity: 0.5 }}>
        <path d="M3 3v18h18" /><path d="M7 16l4-4 4 4 6-6" />
      </svg>
      <p>{message}</p>
    </div>;
  }

  if (data && data.length === 0) {
    return <div className="trend-empty" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ opacity: 0.5 }}>
        <path d="M3 3v18h18" /><path d="M7 16l4-4 4 4 6-6" />
      </svg>
      <p>No date column found for trend analysis.</p>
    </div>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data ?? []}>
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
  );
}
