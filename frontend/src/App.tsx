import { useState } from "react";
import FileUpload from "./components/FileUpload";
import Dashboard from "./components/Dashboard";

type AppState = "upload" | "analyzing" | "dashboard";

export default function App() {
  const [state, setState] = useState<AppState>("upload");
  const [analysisId, setAnalysisId] = useState<string>("");
  const [analysisError, setAnalysisError] = useState("");

  const handleUploadComplete = async (data: {
    analysisId: string;
    columns: string[];
    rowCount: number;
    filename: string;
  }) => {
    setState("analyzing");
    setAnalysisError("");

    try {
      const textCol = data.columns.find((c) => /review|text|comment|feedback|content/i.test(c)) || data.columns[0];
      const ratingCol = data.columns.find((c) => /rating|score|star|rank/i.test(c)) || "";

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_id: data.analysisId,
          text_column: textCol,
          rating_column: ratingCol,
        }),
      });

      const result = await res.json();
      if (!res.ok) throw new Error(result.error);

      setAnalysisId(result.analysis_id);
      setState("dashboard");
    } catch (err: unknown) {
      setAnalysisError(err instanceof Error ? err.message : "Analysis failed");
      setState("upload");
    }
  };

  const handleReset = () => {
    setState("upload");
    setAnalysisId("");
    setAnalysisError("");
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <h1>AnZlyze</h1>
        </div>
        <p className="tagline">Customer Review Intelligence Platform</p>
      </header>

      <main className="app-main">
        {state === "upload" && (
          <>
            {analysisError && <div className="error-banner">{analysisError}</div>}
            <FileUpload onUploadComplete={handleUploadComplete} />
          </>
        )}

        {state === "analyzing" && (
          <div className="analyzing-screen">
            <div className="spinner" />
            <h3>Analyzing your reviews...</h3>
            <div className="pipeline-steps">
              <div className="step active">Text Cleaning</div>
              <div className="step active">TF-IDF Vectorization</div>
              <div className="step active">Model Training</div>
              <div className="step active">Sentiment Prediction</div>
              <div className="step active">Problem Detection</div>
              <div className="step active">Generating Recommendations</div>
            </div>
            <p>This may take a moment for large datasets.</p>
          </div>
        )}

        {state === "dashboard" && analysisId && (
          <Dashboard analysisId={analysisId} onReset={handleReset} />
        )}
      </main>

      <footer className="app-footer">
        <p>AnZlyze — Powered by TF-IDF + Machine Learning</p>
      </footer>
    </div>
  );
}
