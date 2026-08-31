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

function MetricIcon({ name }: { name: string }) {
  const common = {
    width: 18, height: 18, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (name) {
    case "total":
      return <svg {...common}><path d="M22 11 12 3 2 11" /><path d="M5 9v11h14V9" /></svg>;
    case "pos":
      return <svg {...common}><path d="m7 15 3.5-3.5L13 14l3.5-4" /><circle cx="12" cy="12" r="10" /></svg>;
    case "neg":
      return <svg {...common}><path d="m7 9 3.5 3.5L13 10l3.5 4" /><circle cx="12" cy="12" r="10" /></svg>;
    case "neu":
      return <svg {...common}><line x1="5" y1="12" x2="19" y2="12" /><circle cx="12" cy="12" r="10" /></svg>;
    case "acc":
      return <svg {...common}><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></svg>;
    default:
      return <svg {...common}><rect x="8" y="6" width="8" height="14" rx="4" /><path d="M19 7 22 10" /><path d="M5 7 2 10" /></svg>;
  }
}

const METRICS = [
  { key: "total", icon: "total", label: "Total Reviews" },
  { key: "pos", icon: "pos", label: "Positive" },
  { key: "neg", icon: "neg", label: "Negative" },
  { key: "neu", icon: "neu", label: "Neutral" },
  { key: "acc", icon: "acc", label: "Model Accuracy" },
  { key: "bugs", icon: "bugs", label: "Issues Detected" },
];

export default function Dashboard({ analysisId, onReset, onCompare }: Props) {
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
      <div className="fx-page dashboard-page">
        <div className="page-3d" aria-hidden="true">
          <div className="geo geo-wave" />
          <div className="orb orb-2" />
        </div>
        <div className="fx-content-wide">
          <div className="page-title-block">
            <span className="skeleton" style={{ width: 140, height: 28, borderRadius: 30, margin: "0 auto 16px", display: 'block' }} />
            <div className="skeleton skeleton-text wide" style={{ maxWidth: 380, height: 34, margin: "0 auto" }} />
          </div>
          <div className="overview-cards">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="metric-card skeleton-card">
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
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="fx-page dashboard-page">
        <div className="fx-content-wide">
          <div className="error-screen">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--negative)" strokeWidth="1.5" style={{ marginBottom: 16, opacity: 0.8 }}>
              <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <p style={{ marginBottom: 20, color: 'var(--text-secondary)' }}>{error || "No results found"}</p>
            <button className="btn btn-primary" onClick={onReset}>
              Upload New Dataset
            </button>
          </div>
        </div>
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
    <div className="fx-page dashboard-page">
      <div className="page-3d" aria-hidden="true">
        <div className="geo geo-wave" />
        <div className="geo geo-ring" />
        <div className="orb orb-1" />
        <div className="orb orb-3" />
        <div className="grid-floor" />
      </div>

      <div className="fx-content-wide">
        {/* Header */}
        <div className="dashboard-top">
          <div className="page-title-block dash-title">
            <span className="hero-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>Analysis Complete</span>
            </span>
            <h1 className="page-title">
              Analysis <span className="hero-title-gradient">Dashboard</span>
            </h1>
            <div className="dash-chips">
              <span className="dash-chip dash-chip-file">{data.analysis.filename}</span>
              <span className="dash-chip"><strong>{data.analysis.total_reviews.toLocaleString()}</strong> reviews</span>
              <span className="dash-chip">text: <strong>{data.analysis.text_column}</strong></span>
              <span className="dash-chip">rating: <strong>{data.analysis.rating_column || "auto"}</strong></span>
            </div>
          </div>
          <div className="header-actions">
            <ExportButton analysisId={analysisId} />
            <button className="btn btn-secondary action-btn" onClick={() => setShowEmail(true)}>
              <svg className="btn-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="3" />
                <path d="m4 6 8 6 8-6" />
              </svg>
              Email
            </button>
            {onCompare && (
              <button className="btn btn-secondary" onClick={onCompare}>Compare</button>
            )}
            <button className="btn btn-primary" onClick={onReset}>New Analysis</button>
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
            <span className="metric-icon"><MetricIcon name="total" /></span>
            <span className="metric-value">{dist.total.toLocaleString()}</span>
            <span className="metric-label">Total Reviews</span>
          </div>
          <div className="metric-card positive">
            <span className="metric-icon"><MetricIcon name="pos" /></span>
            <span className="metric-value">{dist.positive.toLocaleString()}</span>
            <span className="metric-label">Positive</span>
            <span className="metric-pct">{posPct.toFixed(1)}%</span>
          </div>
          <div className="metric-card negative">
            <span className="metric-icon"><MetricIcon name="neg" /></span>
            <span className="metric-value">{dist.negative.toLocaleString()}</span>
            <span className="metric-label">Negative</span>
            <span className="metric-pct">{negPct.toFixed(1)}%</span>
          </div>
          <div className="metric-card neutral">
            <span className="metric-icon"><MetricIcon name="neu" /></span>
            <span className="metric-value">{dist.neutral.toLocaleString()}</span>
            <span className="metric-label">Neutral</span>
            <span className="metric-pct">{neuPct.toFixed(1)}%</span>
          </div>
          <div className="metric-card acc">
            <span className="metric-icon"><MetricIcon name="acc" /></span>
            <span className="metric-value">
              {currentAccuracy ? `${(currentAccuracy * 100).toFixed(1)}%` : "—"}
            </span>
            <span className="metric-label">Model Accuracy</span>
            <span className="metric-sub">{currentModelName}</span>
          </div>
          <div className="metric-card issues">
            <span className="metric-icon"><MetricIcon name="bugs" /></span>
            <span className="metric-value">{problemCount}</span>
            <span className="metric-label">Issues Detected</span>
          </div>
        </div>

        <div className="tab-bar tab-bar-premium">
          <button
            className={`tab ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
            Overview
          </button>
          <button
            className={`tab ${activeTab === "reviews" ? "active" : ""}`}
            onClick={() => setActiveTab("reviews")}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" />
              <line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" />
              <line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
            </svg>
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
    </div>
  );
}