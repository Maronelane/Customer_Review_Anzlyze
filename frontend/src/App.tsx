import { useState, useCallback } from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import FileUpload from "./components/FileUpload";
import LandingPage from "./components/LandingPage";
import Dashboard from "./components/Dashboard";
import AnalyzingScreen from "./components/AnalyzingScreen";
import CompareView from "./components/CompareView";
import ErrorBoundary from "./components/ErrorBoundary";
import Logo from "./components/Logo";

type AppState = "upload" | "analyzing" | "dashboard" | "compare";

interface UploadData {
  analysisId: string;
  columns: string[];
  rowCount: number;
  filename: string;
  textColumn: string;
  ratingColumn: string;
  customCategories?: Record<string, string[]>;
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
  const { user, logout, loading } = useAuth();
  const [state, setState] = useState<AppState>("upload");
  const [analysisId, setAnalysisId] = useState<string>("");
  const [analysisError, setAnalysisError] = useState("");
  const [authView, setAuthView] = useState<"login" | "register">("login");

  const handleAnalysisProgress = useCallback(() => {
    setState("dashboard");
  }, []);

  const handleAnalysisError = useCallback((msg: string) => {
    setAnalysisError(msg);
    setState("upload");
  }, []);

  if (loading) {
    return (
      <div className="app">
        <div className="loading-screen">
          <div className="spinner" />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="auth-page">
        <header className="app-header">
          <Logo />
          <div className="header-right">
            <ThemeToggle />
            <button
              className={`btn btn-primary btn-sm ${authView === "register" ? "" : "btn-outline-sm"}`}
              onClick={() => setAuthView(authView === "login" ? "register" : "login")}
            >
              {authView === "login" ? "Sign Up" : "Sign In"}
            </button>
          </div>
        </header>
        <main className="app-main landing-main-wrap">
          <LandingPage authView={authView} onSwitch={setAuthView} />
        </main>
      </div>
    );
  }

  const handleUploadComplete = async (data: UploadData) => {
    setAnalysisError("");

    const textCol =
      data.textColumn ||
      data.columns.find((c) => /review|text|comment|feedback|content/i.test(c)) ||
      data.columns[0];
    const ratingCol =
      data.ratingColumn ||
      data.columns.find((c) => /rating|score|star|rank/i.test(c)) ||
      "";

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_id: data.analysisId,
          text_column: textCol,
          rating_column: ratingCol,
          custom_categories: data.customCategories || null,
        }),
      });

      const result = await res.json();
      if (!res.ok) throw new Error(result.error);

      setAnalysisId(data.analysisId);
      setState("analyzing");
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
        <Logo />
        <div className="header-right">
          <div className="user-chip" title={user.username}>
            <span className="avatar">{user.username.charAt(0).toUpperCase()}</span>
            <span className="username">{user.username}</span>
          </div>
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
          <AnalyzingScreen analysisId={analysisId} onComplete={handleAnalysisProgress} onError={handleAnalysisError} />
        )}

        {state === "dashboard" && analysisId && (
          <ErrorBoundary
            fallback={
              <div className="error-screen">
                <p>Dashboard crashed while rendering results.</p>
                <button className="btn btn-primary" onClick={handleReset}>
                  Upload New Dataset
                </button>
              </div>
            }
          >
            <Dashboard
              analysisId={analysisId}
              onReset={handleReset}
              onCompare={() => setState("compare")}
            />
          </ErrorBoundary>
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
