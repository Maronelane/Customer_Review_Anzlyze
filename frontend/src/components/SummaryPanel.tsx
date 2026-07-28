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
      <div className="insight-card">
        <h3>Executive Summary</h3>
        <div className="insight-loading">Generating summary...</div>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="insight-card">
      <h3>Executive Summary</h3>
      <p className="summary-text">{summary}</p>
    </div>
  );
}
