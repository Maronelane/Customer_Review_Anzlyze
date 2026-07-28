import { useState, useEffect } from "react";
import { listAnalyses, type Analysis } from "../api";
import SentimentChart from "./SentimentChart";

interface ComparisonData {
  analysis1: Analysis;
  analysis2: Analysis;
  results1: { sentiment_distribution: { positive: number; negative: number; neutral: number; total: number }; best_model: string; best_accuracy: number; problems: { problems: unknown[] } };
  results2: { sentiment_distribution: { positive: number; negative: number; neutral: number; total: number }; best_model: string; best_accuracy: number; problems: { problems: unknown[] } };
}

interface Props {
  onBack: () => void;
}

export default function CompareView({ onBack }: Props) {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [id1, setId1] = useState("");
  const [id2, setId2] = useState("");
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listAnalyses().then((data) => setAnalyses(data as Analysis[])).catch(() => {});
  }, []);

  const handleCompare = async () => {
    if (!id1 || !id2) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ analysis_id_1: id1, analysis_id_2: id2 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setComparison(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="compare-view">
      <div className="dashboard-header">
        <h2>Compare Datasets</h2>
        <button className="btn btn-secondary" onClick={onBack}>Back</button>
      </div>

      <div className="compare-selectors">
        <div className="config-field">
          <label>Dataset 1</label>
          <select value={id1} onChange={(e) => setId1(e.target.value)}>
            <option value="">Select analysis...</option>
            {analyses.map((a) => (
              <option key={a.id} value={a.id}>{a.filename} ({a.total_reviews || "?"} reviews)</option>
            ))}
          </select>
        </div>
        <div className="config-field">
          <label>Dataset 2</label>
          <select value={id2} onChange={(e) => setId2(e.target.value)}>
            <option value="">Select analysis...</option>
            {analyses.map((a) => (
              <option key={a.id} value={a.id}>{a.filename} ({a.total_reviews || "?"} reviews)</option>
            ))}
          </select>
        </div>
        <button className="btn btn-primary" onClick={handleCompare} disabled={!id1 || !id2 || loading}>
          {loading ? "Comparing..." : "Compare"}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {comparison && (
        <div className="compare-results">
          <div className="compare-grid">
            <div className="compare-col">
              <h3>{comparison.analysis1.filename}</h3>
              <SentimentChart
                distribution={comparison.results1.sentiment_distribution}
                bestModel={comparison.results1.best_model}
                bestAccuracy={comparison.results1.best_accuracy}
              />
            </div>
            <div className="compare-col">
              <h3>{comparison.analysis2.filename}</h3>
              <SentimentChart
                distribution={comparison.results2.sentiment_distribution}
                bestModel={comparison.results2.best_model}
                bestAccuracy={comparison.results2.best_accuracy}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
