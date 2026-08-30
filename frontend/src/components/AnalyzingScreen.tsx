import { useEffect, useState } from "react";
import { getProgress } from "../api";

interface Props {
  analysisId: string;
  onComplete: () => void;
  onError: (msg: string) => void;
}

const PIPELINE = [
  { label: "Text Cleaning", icon: "clean" },
  { label: "TF-IDF Vectorization", icon: "layers" },
  { label: "Model Training", icon: "cpu" },
  { label: "Sentiment Prediction", icon: "thumbs" },
  { label: "Problem Detection", icon: "bug" },
  { label: "Generating Recommendations", icon: "bulb" },
];

function StepIcon({ name }: { name: string }) {
  const common = {
    width: 16, height: 16, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (name) {
    case "clean":
      return <svg {...common}><path d="M3.5 12.5 12 4l8.5 8.5" /><path d="M5 12v6a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-6" /></svg>;
    case "layers":
      return <svg {...common}><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>;
    case "cpu":
      return <svg {...common}><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /><line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" /><line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" /></svg>;
    case "thumbs":
      return <svg {...common}><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3z" /><line x1="7" y1="22" x2="7" y2="11" /></svg>;
    case "bug":
      return <svg {...common}><rect x="8" y="6" width="8" height="14" rx="4" /><path d="M19 7 22 10" /><path d="M5 7 2 10" /><line x1="8" y1="12" x2="16" y2="12" /></svg>;
    default:
      return <svg {...common}><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.4 1 2.3h6c0-.9.4-1.8 1-2.3A7 7 0 0 0 12 2z" /></svg>;
  }
}

export default function AnalyzingScreen({ analysisId, onComplete, onError }: Props) {
  const [step, setStep] = useState("Starting...");
  const [percent, setPercent] = useState(0);

  useEffect(() => {
    let consecutiveErrors = 0;
    const interval = setInterval(async () => {
      try {
        const data = await getProgress(analysisId);
        setStep(data.step);
        setPercent(data.percent);
        consecutiveErrors = 0;
        if (data.step && data.step.toLowerCase().startsWith("error")) {
          clearInterval(interval);
          onError(data.step);
        }
        if (data.status === "error") {
          clearInterval(interval);
          onError(data.step || "Analysis failed");
        }
        if (data.percent >= 100) {
          clearInterval(interval);
          onComplete();
        }
      } catch {
        consecutiveErrors++;
        if (consecutiveErrors > 30) {
          clearInterval(interval);
          onError("Lost connection to server");
        }
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [analysisId, onComplete, onError]);

  const R = 56;
  const C = 2 * Math.PI * R;
  const stepUnit = 100 / PIPELINE.length;

  return (
    <div className="fx-page analyzing-page">
      <div className="page-3d" aria-hidden="true">
        <div className="geo geo-ring" />
        <div className="orb orb-1" />
        <div className="orb orb-3" />
        <div className="grid-floor" />
      </div>

      {/* Floating sentiment chips decoration */}
      <div className="float-chips" aria-hidden="true">
        <div className="float-chip fc-pos">5 &#9733; Positive</div>
        <div className="float-chip fc-neg">1 &#9733; Negative</div>
        <div className="float-chip fc-neu">3 &#9733; Neutral</div>
        <div className="float-chip fc-pos fc-sm">4 &#9733; Positive</div>
      </div>

      <div className="fx-content">
        <div className="analyzing-center">
          <span className="hero-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>ML Pipeline Running</span>
          </span>

          <div className="analyzing-card">
            {/* Circular progress ring */}
            <div className="ring-wrap">
              <svg width="160" height="160" viewBox="0 0 160 160">
                <defs>
                  <linearGradient id="analyzingGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="var(--primary)" />
                    <stop offset="100%" stopColor="var(--positive)" />
                  </linearGradient>
                </defs>
                <circle cx="80" cy="80" r={R} stroke="var(--border-strong)" strokeWidth="10" fill="none" />
                <circle
                  cx="80" cy="80" r={R} stroke="url(#analyzingGrad)" strokeWidth="10" fill="none"
                  strokeLinecap="round" strokeDasharray={C}
                  strokeDashoffset={C * (1 - percent / 100)}
                  transform="rotate(-90 80 80)"
                  style={{ transition: "stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1)" }}
                />
              </svg>
              <div className="ring-center">
                <span className="ring-pct">{Math.round(percent)}%</span>
                <span className="ring-lbl">{percent >= 100 ? "done" : "analysing"}</span>
              </div>
            </div>

            <h3 className="analyzing-title">Analyzing your reviews</h3>
            <p className="analyzing-sub">
              {percent >= 100 ? "Analysis complete — preparing your dashboard..." : "This may take a moment depending on dataset size"}
            </p>

            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${percent}%` }} />
            </div>
            <p className="analyzing-status">{step} ({percent}%)</p>

            {/* Pipeline steps checklist */}
            <div className="pipe-steps">
              {PIPELINE.map((s, i) => {
                const stepPct = (i + 1) * stepUnit;
                const done = percent >= stepPct;
                const current = !done && percent >= i * stepUnit;
                return (
                  <div key={s.label} className={`pipe-step ${done ? "done" : ""} ${current ? "current" : ""}`}>
                    <span className="pipe-icon">
                      {done ? (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      ) : (
                        <StepIcon name={s.icon} />
                      )}
                    </span>
                    <span className="pipe-label">{s.label}</span>
                    {current && <span className="pipe-live"><i /></span>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}