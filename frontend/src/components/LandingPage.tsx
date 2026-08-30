import Login from "./Login";
import Register from "./Register";

interface Props {
  authView: "login" | "register";
  onSwitch: (v: "login" | "register") => void;
}

const STEPS = [
  { icon: "upload", title: "Upload Dataset", desc: "Drop a CSV, Excel, or JSON file of any review collection." },
  { icon: "configure", title: "Configure Columns", desc: "Pick the review text and rating columns — or let auto-detect handle it." },
  { icon: "ml", title: "ML Analysis", desc: "TF-IDF vectorization with SVM, Naive Bayes & Logistic Regression train on the fly." },
  { icon: "insights", title: "Get Insights", desc: "Sentiment breakdown, trending keywords, root-cause issues & smart recommendations." },
];

const FEATURES = [
  { title: "Sentiment Analysis", desc: "Instantly classify every review into Positive, Negative, or Neutral with a trained ML model.", color: "#00d2a0", metric: "92%", metricLabel: "accuracy" },
  { title: "Root-Cause Detection", desc: "Automatically surface the functional issues, performance gaps and build-quality complaints hiding in your reviews.", color: "#6c5ce7", metric: "31", metricLabel: "factors tracked" },
  { title: "Spam & Fake Reviews", desc: "Flag promotional, bot-generated, and duplicate reviews so your insights stay honest.", color: "#ff6b6b", metric: "3x", metricLabel: "faster filtering" },
  { title: "Compare Datasets", desc: "Run two analyses side-by-side and quantify how sentiment, complaints and models change.", color: "#feca57", metric: "1v1", metricLabel: "dataset compare" },
];

const MODULES = [
  { label: "Word Cloud", icon: "cloud", color: "#a29bfe" },
  { label: "Trend Analysis", icon: "trend", color: "#00d2a0" },
  { label: "Problem Detector", icon: "bug", color: "#ff6b6b" },
  { label: "Spam Guard", icon: "shield", color: "#feca57" },
  { label: "Reports", icon: "report", color: "#6c5ce7" },
];

function FeatureIcon({ name }: { name: string }) {
  const common = {
    width: 22, height: 22, viewBox: "0 0 24 24", fill: "none",
    stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (name) {
    case "upload":
      return <svg {...common}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>;
    case "configure":
      return <svg {...common}><path d="M11 6 5 3l-2 4 6 3" /><path d="M23 7 17 4l-2 4 6 3" /><path d="M11 13 5 10l-2 4 6 3" /><path d="M17 10l-2 4 6 3" /><line x1="12" y1="14" x2="12" y2="21" /><line x1="9" y1="21" x2="15" y2="21" /></svg>;
    case "ml":
      return <svg {...common}><circle cx="12" cy="12" r="10" /><line x1="12" y1="2" x2="12" y2="22" /><line x1="2" y1="12" x2="22" y2="12" /></svg>;
    case "insights":
      return <svg {...common}><path d="M22 11.1V12a10 10 0 1 1-5.9-9.1" /><polyline points="22 4 12 14 9 11" /></svg>;
    case "cloud":
      return <svg {...common}><path d="M17.5 19a4.5 4.5 0 1 0 0-9 5.5 5.5 0 0 0-10.7 1A3.5 3.5 0 0 0 6.5 19" /></svg>;
    case "trend":
      return <svg {...common}><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" /></svg>;
    case "bug":
      return <svg {...common}><rect x="8" y="6" width="8" height="14" rx="4" /><path d="M19 7 22 10" /><path d="M5 7 2 10" /><line x1="8" y1="12" x2="16" y2="12" /></svg>;
    case "shield":
      return <svg {...common}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" /></svg>;
    case "report":
      return <svg {...common}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></svg>;
    case "person":
      return <svg {...common}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>;
    case "lock":
      return <svg {...common}><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>;
    case "spark":
      return <svg {...common}><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /></svg>;
    default:
      return <svg {...common}><circle cx="12" cy="12" r="10" /></svg>;
  }
}

export default function LandingPage({ authView, onSwitch }: Props) {
  return (
    <div className="landing">
      {/* 3D decoration: floating geometric shapes */}
      <div className="landing-3d" aria-hidden="true">
        <div className="geo geo-pyramid" />
        <div className="geo geo-cube" />
        <div className="geo geo-ring" />
        <div className="geo geo-wave" />
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
        <div className="orb orb-4" />
        <div className="grid-floor" />
      </div>

      <main className="landing-main">
        {/* Hero / product showcase */}
        <section className="landing-hero">
          <div className="hero-badge">
            <FeatureIcon name="spark" />
            <span>Customer Review Intelligence, Powered by ML</span>
          </div>

          <h1 className="hero-title">
            Decode your customer reviews,
            <br />
            <span className="hero-title-gradient">unlock real insights</span>
          </h1>

          <p className="hero-subtitle">
            AnZlyze uploads any review dataset and turns raw text into actionable business decisions — sentiment,
            root causes, trend keywords, and spam filtering — all automatically.
          </p>

          <div className="hero-cta">
            <button className="btn btn-primary btn-lg" onClick={() => onSwitch("register")}>
              Get Started Free
            </button>
            <button className="btn btn-ghost btn-lg" onClick={() => onSwitch("login")}>
              <FeatureIcon name="lock" /> Sign In
            </button>
          </div>

          {/* Animated stat counters */}
          <div className="hero-stats">
            <div className="hero-stat"><span className="hero-stat-val">4</span><span className="hero-stat-lbl">ML pipelines</span></div>
            <div className="hero-stat"><span className="hero-stat-val">99%</span><span className="hero-stat-lbl">uptime</span></div>
            <div className="hero-stat"><span className="hero-stat-val">∞</span><span className="hero-stat-lbl">reviews scale</span></div>
            <div className="hero-stat"><span className="hero-stat-val">10k+</span><span className="hero-stat-lbl">rows / dataset</span></div>
          </div>

          {/* How it works */}
          <div className="how-it-works">
            <h2 className="section-eyebrow">How it works</h2>
            <div className="steps-grid">
              {STEPS.map((s, i) => (
                <div className="step-card" key={s.title} style={{ animationDelay: `${i * 90}ms` }}>
                  <div className="step-icon"><FeatureIcon name={s.icon} /></div>
                  <span className="step-num">0{i + 1}</span>
                  <h3>{s.title}</h3>
                  <p>{s.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Features showcase */}
          <div className="features">
            <h2 className="section-heading">Everything you need from every review</h2>
            <p className="section-sub">A complete analytics suite under one roof</p>
            <div className="features-grid">
              {FEATURES.map((f, i) => (
                <div className="feature-card" key={f.title} style={{ animationDelay: `${i * 80}ms` }}>
                  <div className="feature-card-top">
                    <span className="feature-chip" style={{ background: `${f.color}1f`, color: f.color, boxShadow: `0 0 0 1px ${f.color}33` }}>
                      {f.title}
                    </span>
                    <span className="feature-metric" style={{ color: f.color }}>{f.metric}</span>
                  </div>
                  <p className="feature-desc">{f.desc}</p>
                  <span className="feature-metric-label">{f.metricLabel}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Module buttons */}
          <div className="modules">
            <h2 className="section-eyebrow">Explore the modules</h2>
            <div className="module-row">
              {MODULES.map((m, i) => (
                <button
                  key={m.label}
                  className="module-btn"
                  style={{ animationDelay: `${i * 60}ms`, "--mod-color": m.color } as React.CSSProperties}
                  onClick={() => onSwitch("register")}
                >
                  <span className="module-icon" style={{ background: `${m.color}1f`, color: m.color }}><FeatureIcon name={m.icon} /></span>
                  <span>{m.label}</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Auth panel on the right */}
        <section className="landing-auth">
          <div className="landing-auth-card">
            <div className="auth-visual">
              <span className="auth-logo-glow" />
              <div className="auth-group">
                {authView === "login" ? (
                  <Login onSwitch={() => onSwitch("register")} />
                ) : (
                  <Register onSwitch={() => onSwitch("login")} />
                )}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
