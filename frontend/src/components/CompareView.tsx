import { useState, useEffect } from "react";
import { listAnalyses, type Analysis } from "../api";
import SentimentChart from "./SentimentChart";

interface Delta {
  label: string;
  value1: number;
  value2: number;
  diff: number;
  type: string;
  better?: string;
}

interface ComparisonData {
  analysis1: Analysis;
  analysis2: Analysis;
  results1: {
    sentiment_distribution: { positive: number; negative: number; neutral: number; total: number };
    best_model: string;
    best_accuracy: number;
    problems: { problems: { category: string; category_key: string; frequency: number; percentage: number }[]; top_complaint_words: { word: string; count: number }[] };
    spam_summary: { flagged_percentage: number; total_flagged: number; total_reviews: number };
    cluster_summary: unknown[];
  };
  results2: {
    sentiment_distribution: { positive: number; negative: number; neutral: number; total: number };
    best_model: string;
    best_accuracy: number;
    problems: { problems: { category: string; category_key: string; frequency: number; percentage: number }[]; top_complaint_words: { word: string; count: number }[] };
    spam_summary: { flagged_percentage: number; total_flagged: number; total_reviews: number };
    cluster_summary: unknown[];
  };
  deltas: {
    sentiment: {
      dataset1: { positive: number; negative: number; neutral: number };
      dataset2: { positive: number; negative: number; neutral: number };
    };
    problems: { shared: string[]; only_in_dataset1: string[]; only_in_dataset2: string[] };
    complaint_words: { shared: string[]; only_in_dataset1: string[]; only_in_dataset2: string[] };
    spam: { dataset1_rate: number; dataset2_rate: number; dataset1_flagged: number; dataset2_flagged: number };
    models: { dataset1_name: string; dataset1_accuracy: number; dataset2_name: string; dataset2_accuracy: number };
    summary: Delta[];
  };
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
    listAnalyses()
      .then((data) => setAnalyses(data as Analysis[]))
      .catch(() => {});
  }, []);

  const handleCompare = async () => {
    if (!id1 || !id2) return;
    if (id1 === id2) {
      setError("Please select two different datasets to compare.");
      return;
    }
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

  const diffBadge = (diff: number, better?: string, invert?: boolean) => {
    if (diff === 0) return null;
    const effectiveBetter = invert ? (better === "higher" ? "lower" : "higher") : better;
    const isGood =
      (effectiveBetter === "higher" && diff > 0) ||
      (effectiveBetter === "lower" && diff < 0);
    const cls = isGood ? "delta-positive" : diff === 0 ? "" : "delta-negative";
    const sign = diff > 0 ? "+" : "";
    return <span className={`compare-delta ${cls}`}>{sign}{diff}{typeof diff === "number" && Math.abs(diff) < 10 ? "%" : ""}</span>;
  };

  const formatCat = (key: string) => key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

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
              <option key={a.id} value={a.id}>
                {a.filename} ({a.total_reviews || "?"} reviews)
              </option>
            ))}
          </select>
        </div>
        <div className="config-field">
          <label>Dataset 2</label>
          <select value={id2} onChange={(e) => setId2(e.target.value)}>
            <option value="">Select analysis...</option>
            {analyses.map((a) => (
              <option key={a.id} value={a.id}>
                {a.filename} ({a.total_reviews || "?"} reviews)
              </option>
            ))}
          </select>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleCompare}
          disabled={!id1 || !id2 || loading}
        >
          {loading ? "Comparing..." : "Compare"}
        </button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {loading && (
        <div className="compare-loading">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton skeleton-card" style={{ height: 120 }} />
          ))}
        </div>
      )}

      {comparison && (
        <div className="compare-results">
          {/* Summary Delta Bar */}
          <div className="compare-summary-bar">
            {comparison.deltas.summary.map((d, i) => (
              <div key={i} className="compare-summary-item">
                <span className="compare-summary-label">{d.label}</span>
                <div className="compare-summary-values">
                  <span className="compare-summary-val">{d.value1}{d.type === "pct" ? "%" : ""}</span>
                  <span className="compare-summary-vs">vs</span>
                  <span className="compare-summary-val">{d.value2}{d.type === "pct" ? "%" : ""}</span>
                </div>
                {diffBadge(d.diff, d.better)}
              </div>
            ))}
          </div>

          {/* Sentiment Side-by-Side */}
          <div className="compare-section">
            <h3>Sentiment Distribution</h3>
            <div className="compare-grid">
              <div className="compare-col">
                <h4>{comparison.analysis1.filename}</h4>
                <SentimentChart
                  distribution={comparison.results1.sentiment_distribution}
                  bestModel={comparison.results1.best_model}
                  bestAccuracy={comparison.results1.best_accuracy}
                />
              </div>
              <div className="compare-col">
                <h4>{comparison.analysis2.filename}</h4>
                <SentimentChart
                  distribution={comparison.results2.sentiment_distribution}
                  bestModel={comparison.results2.best_model}
                  bestAccuracy={comparison.results2.best_accuracy}
                />
              </div>
            </div>
          </div>

          {/* Spam Comparison */}
          <div className="compare-section">
            <h3>Spam &amp; Fake Reviews</h3>
            <div className="compare-spam-grid">
              <div className="compare-spam-col">
                <div className="compare-spam-rate">
                  <span className="compare-spam-pct" style={{ color: comparison.deltas.spam.dataset1_rate > 10 ? "var(--negative)" : "var(--positive)" }}>
                    {comparison.deltas.spam.dataset1_rate}%
                  </span>
                  <span className="compare-spam-label">flagged</span>
                </div>
                <span className="compare-spam-detail">{comparison.deltas.spam.dataset1_flagged} of {comparison.results1.sentiment_distribution.total} reviews</span>
              </div>
              <div className="compare-spam-divider">
                {diffBadge(comparison.deltas.spam.dataset2_rate - comparison.deltas.spam.dataset1_rate, "lower", true)}
              </div>
              <div className="compare-spam-col">
                <div className="compare-spam-rate">
                  <span className="compare-spam-pct" style={{ color: comparison.deltas.spam.dataset2_rate > 10 ? "var(--negative)" : "var(--positive)" }}>
                    {comparison.deltas.spam.dataset2_rate}%
                  </span>
                  <span className="compare-spam-label">flagged</span>
                </div>
                <span className="compare-spam-detail">{comparison.deltas.spam.dataset2_flagged} of {comparison.results2.sentiment_distribution.total} reviews</span>
              </div>
            </div>
          </div>

          {/* Model Comparison */}
          <div className="compare-section">
            <h3>Model Performance</h3>
            <div className="compare-model-grid">
              <div className="compare-model-col">
                <span className="compare-model-name">{comparison.deltas.models.dataset1_name}</span>
                <span className="compare-model-acc">{comparison.deltas.models.dataset1_accuracy}%</span>
              </div>
              <div className="compare-model-divider">
                {diffBadge(comparison.deltas.models.dataset2_accuracy - comparison.deltas.models.dataset1_accuracy, "higher")}
              </div>
              <div className="compare-model-col">
                <span className="compare-model-name">{comparison.deltas.models.dataset2_name}</span>
                <span className="compare-model-acc">{comparison.deltas.models.dataset2_accuracy}%</span>
              </div>
            </div>
          </div>

          {/* Problems Overlap */}
          <div className="compare-section">
            <h3>Problem Categories Overlap</h3>
            {comparison.deltas.problems.shared.length === 0 &&
             comparison.deltas.problems.only_in_dataset1.length === 0 &&
             comparison.deltas.problems.only_in_dataset2.length === 0 ? (
              <p className="compare-empty">No problems detected in either dataset.</p>
            ) : (
              <div className="compare-overlap">
                {comparison.deltas.problems.shared.length > 0 && (
                  <div className="overlap-group overlap-shared">
                    <span className="overlap-badge">Shared ({comparison.deltas.problems.shared.length})</span>
                    <div className="overlap-tags">
                      {comparison.deltas.problems.shared.map((k) => (
                        <span key={k} className="overlap-tag shared">{formatCat(k)}</span>
                      ))}
                    </div>
                  </div>
                )}
                {comparison.deltas.problems.only_in_dataset1.length > 0 && (
                  <div className="overlap-group overlap-only1">
                    <span className="overlap-badge">Only in Dataset 1 ({comparison.deltas.problems.only_in_dataset1.length})</span>
                    <div className="overlap-tags">
                      {comparison.deltas.problems.only_in_dataset1.map((k) => (
                        <span key={k} className="overlap-tag only1">{formatCat(k)}</span>
                      ))}
                    </div>
                  </div>
                )}
                {comparison.deltas.problems.only_in_dataset2.length > 0 && (
                  <div className="overlap-group overlap-only2">
                    <span className="overlap-badge">Only in Dataset 2 ({comparison.deltas.problems.only_in_dataset2.length})</span>
                    <div className="overlap-tags">
                      {comparison.deltas.problems.only_in_dataset2.map((k) => (
                        <span key={k} className="overlap-tag only2">{formatCat(k)}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Complaint Keywords Overlap */}
          <div className="compare-section">
            <h3>Top Complaint Keywords Overlap</h3>
            {comparison.deltas.complaint_words.shared.length === 0 &&
             comparison.deltas.complaint_words.only_in_dataset1.length === 0 &&
             comparison.deltas.complaint_words.only_in_dataset2.length === 0 ? (
              <p className="compare-empty">No complaint keywords detected.</p>
            ) : (
              <div className="compare-overlap">
                {comparison.deltas.complaint_words.shared.length > 0 && (
                  <div className="overlap-group overlap-shared">
                    <span className="overlap-badge">Shared ({comparison.deltas.complaint_words.shared.length})</span>
                    <div className="overlap-tags">
                      {comparison.deltas.complaint_words.shared.map((w) => (
                        <span key={w} className="overlap-tag shared">{w}</span>
                      ))}
                    </div>
                  </div>
                )}
                {comparison.deltas.complaint_words.only_in_dataset1.length > 0 && (
                  <div className="overlap-group overlap-only1">
                    <span className="overlap-badge">Only in Dataset 1 ({comparison.deltas.complaint_words.only_in_dataset1.length})</span>
                    <div className="overlap-tags">
                      {comparison.deltas.complaint_words.only_in_dataset1.map((w) => (
                        <span key={w} className="overlap-tag only1">{w}</span>
                      ))}
                    </div>
                  </div>
                )}
                {comparison.deltas.complaint_words.only_in_dataset2.length > 0 && (
                  <div className="overlap-group overlap-only2">
                    <span className="overlap-badge">Only in Dataset 2 ({comparison.deltas.complaint_words.only_in_dataset2.length})</span>
                    <div className="overlap-tags">
                      {comparison.deltas.complaint_words.only_in_dataset2.map((w) => (
                        <span key={w} className="overlap-tag only2">{w}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
