import { useState, useEffect } from "react";
import { getResults, type ResultsData } from "../api";
import SentimentChart from "./SentimentChart";
import ProblemList from "./ProblemList";
import Recommendations from "./Recommendations";
import ReviewTable from "./ReviewTable";
import ExportButton from "./ExportButton";
import EmailModal from "./EmailModal";
import TrendChart from "./TrendChart";
import WordCloud from "./WordCloud";
import SummaryPanel from "./SummaryPanel";

interface Props {
  analysisId: string;
  onReset: () => void;
  onCompare?: () => void;
}

export default function Dashboard({ analysisId, onReset }: Props) {
  const [data, setData] = useState<ResultsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "reviews">("overview");
  const [showEmail, setShowEmail] = useState(false);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const results = await getResults(analysisId);
        setData(results);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load results");
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, [analysisId]);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading analysis results...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="error-screen">
        <p>{error || "No results found"}</p>
        <button className="btn btn-primary" onClick={onReset}>
          Upload New Dataset
        </button>
      </div>
    );
  }

  const { results } = data;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="header-left">
          <h2>Analysis Dashboard</h2>
          <p className="header-meta">
            {data.analysis.filename} — {data.analysis.total_reviews} reviews analyzed
          </p>
        </div>
        <div className="header-actions">
          <ExportButton analysisId={analysisId} />
          <button className="btn btn-secondary" onClick={() => setShowEmail(true)}>
            Email
          </button>
          <button className="btn btn-secondary" onClick={onReset}>
            New Analysis
          </button>
        </div>
      </div>

      <div className="overview-cards">
        <div className="metric-card">
          <span className="metric-value">{results.sentiment_distribution.total}</span>
          <span className="metric-label">Total Reviews</span>
        </div>
        <div className="metric-card positive">
          <span className="metric-value">{results.sentiment_distribution.positive}</span>
          <span className="metric-label">Positive</span>
        </div>
        <div className="metric-card negative">
          <span className="metric-value">{results.sentiment_distribution.negative}</span>
          <span className="metric-label">Negative</span>
        </div>
        <div className="metric-card neutral">
          <span className="metric-value">{results.sentiment_distribution.neutral}</span>
          <span className="metric-label">Neutral</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{results.best_accuracy ? `${(results.best_accuracy * 100).toFixed(1)}%` : "—"}</span>
          <span className="metric-label">Model Accuracy</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{results.problems?.problems?.length ?? 0}</span>
          <span className="metric-label">Problems Found</span>
        </div>
      </div>

      <div className="tab-bar">
        <button
          className={`tab ${activeTab === "overview" ? "active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          Overview
        </button>
        <button
          className={`tab ${activeTab === "reviews" ? "active" : ""}`}
          onClick={() => setActiveTab("reviews")}
        >
          Review Details
        </button>
      </div>

      {activeTab === "overview" ? (
        <div className="dashboard-grid">
          <SummaryPanel analysisId={analysisId} />
          <SentimentChart
            distribution={results.sentiment_distribution}
            bestModel={results.best_model}
            bestAccuracy={results.best_accuracy}
          />
          <TrendChart analysisId={analysisId} />
          <WordCloud analysisId={analysisId} />
          <ProblemList
            problems={results.problems?.problems ?? []}
            topWords={results.problems?.top_complaint_words ?? []}
          />
          <div className="full-width">
            <Recommendations
              recommendations={results.recommendations?.recommendations ?? []}
              summary={results.recommendations?.summary ?? ""}
            />
          </div>
        </div>
      ) : (
        <ReviewTable analysisId={analysisId} />
      )}

      {showEmail && (
        <EmailModal analysisId={analysisId} onClose={() => setShowEmail(false)} />
      )}
    </div>
  );
}
