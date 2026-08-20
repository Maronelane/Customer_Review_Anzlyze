import { useState, useEffect, useCallback } from "react";
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
import ModelSelector from "./ModelSelector";

interface Props {
  analysisId: string;
  onReset: () => void;
  onCompare?: () => void;
}

const MODEL_DISPLAY: Record<string, string> = {
  naive_bayes: "Naive Bayes",
  logistic_regression: "Logistic Regression",
  svm: "Support Vector Machine",
};

export default function Dashboard({ analysisId, onReset }: Props) {
  const [data, setData] = useState<ResultsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "reviews">("overview");
  const [showEmail, setShowEmail] = useState(false);
  const [activeModel, setActiveModel] = useState<string>("");

  const fetchResults = useCallback(async (model?: string) => {
    try {
      const results = await getResults(analysisId, model);
      setData(results);
      if (!activeModel && results.results.active_model) {
        setActiveModel(results.results.active_model);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load results");
    } finally {
      setLoading(false);
    }
  }, [analysisId, activeModel]);

  useEffect(() => {
    setLoading(true);
    fetchResults();
  }, [analysisId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleModelSelect = useCallback((modelName: string) => {
    setActiveModel(modelName);
    setLoading(true);
    fetchResults(modelName);
  }, [fetchResults]);

  if (loading && !data) {
    return (
      <div className="dashboard">
        <div className="dashboard-header">
          <div>
            <div className="skeleton skeleton-text" style={{ width: 200, height: 24, marginBottom: 8 }} />
            <div className="skeleton skeleton-text" style={{ width: 300, height: 14 }} />
          </div>
        </div>
        <div className="overview-cards">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="metric-card">
              <div className="skeleton skeleton-text" style={{ width: 60, height: 24 }} />
              <div className="skeleton skeleton-text short" style={{ height: 10, marginTop: 8 }} />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 60, borderRadius: 'var(--radius)' }} />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="error-screen">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--negative)" strokeWidth="1.5" style={{ marginBottom: 16, opacity: 0.8 }}>
          <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
        </svg>
        <p style={{ marginBottom: 20, color: 'var(--text-secondary)' }}>{error || "No results found"}</p>
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

  const currentAccuracy = results.model_results?.[activeModel]?.accuracy ?? results.best_accuracy;
  const currentModelName = MODEL_DISPLAY[activeModel] || activeModel.replace("_", " ");

  const modelEntries = results.model_results
    ? Object.entries(results.model_results).map(([name, info]) => ({
        name,
        displayName: MODEL_DISPLAY[name] || name.replace(/_/g, " "),
        accuracy: info.accuracy,
        isBest: name === results.best_model,
      }))
    : [];

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

      {modelEntries.length > 0 && (
        <ModelSelector
          models={modelEntries}
          activeModel={activeModel}
          onSelect={handleModelSelect}
          hasModelRuns={!!results.model_runs && Object.keys(results.model_runs).length > 0}
        />
      )}

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
            {currentAccuracy ? `${(currentAccuracy * 100).toFixed(1)}%` : "—"}
          </span>
          <span className="metric-label">Model Accuracy</span>
          <span className="metric-sub">{currentModelName}</span>
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
                <SummaryPanel analysisId={analysisId} activeModel={activeModel} />
              </CollapsibleCard>
            </ErrorBoundary>
          </div>
          <ErrorBoundary>
            <CollapsibleCard
              title="Sentiment Distribution"
              subtitle={`${currentModelName} — ${currentAccuracy ? (currentAccuracy * 100).toFixed(1) : "—"}%`}
            >
              <SentimentChart
                distribution={dist}
                bestModel={activeModel}
                bestAccuracy={currentAccuracy}
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
              <WordCloud analysisId={analysisId} activeModel={activeModel} />
            </CollapsibleCard>
          </ErrorBoundary>
          <ErrorBoundary>
            <CollapsibleCard
              title="Spam / Fake Detection"
              subtitle={currentModelName}
            >
              <SpamDetection analysisId={analysisId} activeModel={activeModel} />
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
        <ReviewTable analysisId={analysisId} activeModel={activeModel} />
      )}

      {showEmail && (
        <EmailModal analysisId={analysisId} onClose={() => setShowEmail(false)} />
      )}
    </div>
  );
}
