import { useState, useEffect } from "react";
import { getAiSummary } from "../api";

interface Props {
  analysisId: string;
}

export default function SummaryPanel({ analysisId }: Props) {
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAiSummary(analysisId)
      .then((res) => setSummary(res.summary))
      .catch(() => setSummary(""))
      .finally(() => setLoading(false));
  }, [analysisId]);

  if (loading) {
    return (
      <div className="summary-loading">
        <div className="summary-skeleton-line" />
        <div className="summary-skeleton-line short" />
        <div className="summary-skeleton-line" />
      </div>
    );
  }

  if (!summary) return null;

  const lines = summary.split("\n").filter(Boolean);
  const title = lines[0] || "";
  const body = lines.slice(1);

  return (
    <>
      <div className="summary-header">
        <h3>Executive Summary</h3>
      </div>
      <div className="summary-content">
        {body.map((line, i) => {
          const trimmed = line.trim();
          if (trimmed.startsWith("WARNING:") || trimmed.startsWith("CAUTION:")) {
            return (
              <p key={i} className={`summary-alert ${trimmed.startsWith("WARNING") ? "danger" : "warning"}`}>
                {trimmed}
              </p>
            );
          }
          if (trimmed.startsWith("Primary Focus:") || trimmed.startsWith("Top problem")) {
            return <p key={i} className="summary-focus">{trimmed}</p>;
          }
          if (trimmed.includes("%")) {
            return <p key={i} className="summary-metrics">{trimmed}</p>;
          }
          return <p key={i} className="summary-body">{trimmed}</p>;
        })}
      </div>
    </>
  );
}
