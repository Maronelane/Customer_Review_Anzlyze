interface ModelInfo {
  name: string;
  displayName: string;
  accuracy: number;
  isBest: boolean;
}

interface Props {
  models: ModelInfo[];
  activeModel: string;
  onSelect: (modelName: string) => void;
  hasModelRuns?: boolean;
}

const MODEL_ICONS: Record<string, string> = {
  naive_bayes: "NB",
  logistic_regression: "LR",
  svm: "SVM",
};

const MODEL_COLORS: Record<string, string> = {
  naive_bayes: "#6c5ce7",
  logistic_regression: "#00d2a0",
  svm: "#ff6b6b",
};

export default function ModelSelector({ models, activeModel, onSelect, hasModelRuns }: Props) {
  return (
    <div className="model-selector">
      <div className="model-selector-header">
        <h3 className="model-selector-title">Choose Model</h3>
        {!hasModelRuns && (
          <span className="model-selector-hint">Run a new analysis to compare all models</span>
        )}
      </div>
      <div className="model-cards">
        {models.map((m) => {
          const isActive = m.name === activeModel;
          return (
            <button
              key={m.name}
              className={`model-card ${isActive ? "active" : ""} ${!hasModelRuns && !m.isBest ? "disabled" : ""}`}
              onClick={() => onSelect(m.name)}
              style={{ "--model-color": MODEL_COLORS[m.name] || "var(--primary)" } as React.CSSProperties}
            >
              <div className="model-card-icon">
                {MODEL_ICONS[m.name] || m.name[0]?.toUpperCase()}
              </div>
              <div className="model-card-info">
                <span className="model-card-name">{m.displayName}</span>
                <span className="model-card-acc">{(m.accuracy * 100).toFixed(1)}%</span>
              </div>
              {m.isBest && <span className="model-card-best">BEST</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
