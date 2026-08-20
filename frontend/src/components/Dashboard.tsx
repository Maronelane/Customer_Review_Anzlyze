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
import SpamDetection from "./SpamDetection";
import ErrorBoundary from "./ErrorBoundary";
import CollapsibleCard from "./CollapsibleCard";

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
  const dist = results.sentiment_distribution;
  const posPct = dist.total ? (dist.positive / dist.total) * 100 : 0;
  const negPct = dist.total ? (dist.negative / dist.total) * 100 : 0;
  const neuPct = dist.total ? (dist.neutral / dist.total) * 100 : 0;
  const problemCount = results.problems?.problems?.length ?? 0;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="header-left">
          <h2>Analysis Dashboard</h2>
          <p className="header-meta">
            {data.analysis.filename} — {data.analysis.total_reviews.toLocaleString()} reviews analyzed
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
        <div className="metric-card total">
          <span className="metric-value">{dist.total.toLocaleString()}</span>
          <span className="metric-label">Total Reviews</span>
        </div>
        <div className="metric-card positive">
          <span className="metric-value">{dist.positive.toLocaleString()}</span>
          <span className="metric-label">Positive</span>
          <span className="metric-pct">{posPct.toFixed(1)}%</span>
        </div>
        <div className="metric-card negative">
          <span className="metric-value">{dist.negative.toLocaleString()}</span>
          <span className="metric-label">Negative</span>
          <span className="metric-pct">{negPct.toFixed(1)}%</span>
        </div>
        <div className="metric-card neutral">
          <span className="metric-value">{dist.neutral.toLocaleString()}</span>
          <span className="metric-label">Neutral</span>
          <span className="metric-pct">{neuPct.toFixed(1)}%</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">
            {results.best_accuracy ? `${(results.best_accuracy * 100).toFixed(1)}%` : "—"}
          </span>
          <span className="metric-label">Model Accuracy</span>
          <span className="metric-sub">{results.best_model?.replace("_", " ")}</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{problemCount}</span>
          <span className="metric-label">Issues Detected</span>
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
          <div className="grid-span-full">
            <ErrorBoundary>
              <CollapsibleCard title="Executive Summary" defaultOpen>
                <SummaryPanel analysisId={analysisId} />
              </CollapsibleCard>
            </ErrorBoundary>
          </div>
          <ErrorBoundary>
            <CollapsibleCard
              title="Sentiment Distribution"
              subtitle={`${results.best_model?.replace("_", " ") || "model"} — ${results.best_accuracy ? (results.best_accuracy * 100).toFixed(1) : "—"}%`}
            >
              <SentimentChart
                distribution={dist}
                bestModel={results.best_model}
                bestAccuracy={results.best_accuracy}
              />
            </CollapsibleCard>
          </ErrorBoundary>
          <ErrorBoundary>
            <CollapsibleCard title="Sentiment Trend">
              <TrendChart analysisId={analysisId} />
            </CollapsibleCard>
          </ErrorBoundary>
          <ErrorBoundary>
            <CollapsibleCard title="Word Cloud">
              <WordCloud analysisId={analysisId} />
            </CollapsibleCard>
          </ErrorBoundary>
          <ErrorBoundary>
            <CollapsibleCard
              title="Spam / Fake Detection"
              subtitle={results.best_model?.replace("_", " ") || undefined}
            >
              <SpamDetection analysisId={analysisId} />
            </CollapsibleCard>
          </ErrorBoundary>
          <div className="grid-span-full">
            <ErrorBoundary>
              <CollapsibleCard
                title="Problem Detection"
                subtitle={problemCount > 0 ? `${problemCount} issues found` : undefined}
              >
                <ProblemList
                  problems={results.problems?.problems ?? []}
                  topWords={results.problems?.top_complaint_words ?? []}
                />
              </CollapsibleCard>
            </ErrorBoundary>
          </div>
          <div className="grid-span-full">
            <ErrorBoundary>
              <CollapsibleCard title="Recommendations">
                <Recommendations
                  recommendations={results.recommendations?.recommendations ?? []}
                  summary={results.recommendations?.summary ?? ""}
                />
              </CollapsibleCard>
            </ErrorBoundary>
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
