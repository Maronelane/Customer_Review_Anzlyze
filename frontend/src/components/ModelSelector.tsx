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

export default function ModelSelector({ models, activeModel, onSelect }: Props) {
  return (
    <div className="model-selector">
      <h3 className="model-selector-title">Choose Model</h3>
      <div className="model-cards">
        {models.map((m) => {
          const isActive = m.name === activeModel;
          return (
            <button
              key={m.name}
              className={`model-card ${isActive ? "active" : ""}`}
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
