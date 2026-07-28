import { useState, useEffect, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import Login from "./components/Login";
import Register from "./components/Register";
import FileUpload from "./components/FileUpload";
import Dashboard from "./components/Dashboard";
import CompareView from "./components/CompareView";
import { getProgress } from "./api";

type AppState = "upload" | "analyzing" | "dashboard" | "compare";

function AnalyzingScreen({ analysisId, onComplete }: { analysisId: string; onComplete: () => void }) {
  const [step, setStep] = useState("Starting...");
  const [percent, setPercent] = useState(0);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await getProgress(analysisId);
        setStep(data.step);
        setPercent(data.percent);
        if (data.percent >= 100) {
          clearInterval(interval);
          onComplete();
        }
      } catch { /* ignore */ }
    }, 1500);
    return () => clearInterval(interval);
  }, [analysisId, onComplete]);

  const steps = ["Text Cleaning", "TF-IDF Vectorization", "Model Training", "Sentiment Prediction", "Problem Detection", "Generating Recommendations"];

  return (
    <div className="analyzing-screen">
      <div className="spinner" />
      <h3>Analyzing your reviews...</h3>
      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${percent}%` }} />
      </div>
      <p className="progress-step">{step} ({percent}%)</p>
      <div className="pipeline-steps">
        {steps.map((s, i) => {
          const stepPct = ((i + 1) / steps.length) * 100;
          return (
            <div key={s} className={`step ${percent >= stepPct ? "active" : ""}`}>{s}</div>
          );
        })}
      </div>
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button className="theme-toggle" onClick={toggle} title="Toggle theme">
      {theme === "dark" ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}

function MainApp() {
  const { user, logout } = useAuth();
  const [state, setState] = useState<AppState>("upload");
  const [analysisId, setAnalysisId] = useState<string>("");
  const [analysisError, setAnalysisError] = useState("");
  const [authView, setAuthView] = useState<"login" | "register">("login");

  if (!user) {
    return (
      <div className="auth-page">
        <header className="app-header">
          <div className="logo">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <h1>AnZlyze</h1>
          </div>
          <ThemeToggle />
        </header>
        <main className="app-main">
          {authView === "login" ? (
            <Login onSwitch={() => setAuthView("register")} />
          ) : (
            <Register onSwitch={() => setAuthView("login")} />
          )}
        </main>
      </div>
    );
  }

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

      const token = localStorage.getItem("auth");
      const parsed = token ? JSON.parse(token) : null;

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(parsed?.token ? { Authorization: `Bearer ${parsed.token}` } : {}),
        },
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

  const handleAnalysisProgress = useCallback(() => {
    setState("dashboard");
  }, []);

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
        <div className="header-right">
          <span className="username">{user.username}</span>
          <ThemeToggle />
          <button className="btn btn-secondary btn-sm" onClick={logout}>Logout</button>
        </div>
      </header>

      <main className="app-main">
        {state === "upload" && (
          <>
            {analysisError && <div className="error-banner">{analysisError}</div>}
            <FileUpload onUploadComplete={handleUploadComplete} />
            <div className="extra-actions">
              <button className="btn btn-secondary" onClick={() => setState("compare")}>
                Compare Datasets
              </button>
            </div>
          </>
        )}

        {state === "analyzing" && analysisId && (
          <AnalyzingScreen analysisId={analysisId} onComplete={handleAnalysisProgress} />
        )}

        {state === "dashboard" && analysisId && (
          <Dashboard
            analysisId={analysisId}
            onReset={handleReset}
            onCompare={() => setState("compare")}
          />
        )}

        {state === "compare" && (
          <CompareView onBack={() => setState("upload")} />
        )}
      </main>

      <footer className="app-footer">
        <p>AnZlyze — Powered by TF-IDF + Machine Learning</p>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <MainApp />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
