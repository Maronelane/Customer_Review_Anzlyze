import React, { useState, useRef, useCallback } from "react";

interface Props {
  onUploadComplete: (data: {
    analysisId: string;
    columns: string[];
    rowCount: number;
    preview: Record<string, unknown>[];
    filename: string;
    textColumn: string;
    ratingColumn: string;
    customCategories?: Record<string, string[]>;
  }) => void;
}

const STEPS = ["Select File", "Configure", "Analyze"];
const SUPPORTED = ["CSV", "Excel (.xlsx)", "JSON"];

export default function FileUpload({ onUploadComplete }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [preview, setPreview] = useState<Record<string, unknown>[]>([]);
  const [rowCount, setRowCount] = useState(0);
  const [analysisId, setAnalysisId] = useState<string>("");
  const [filename, setFilename] = useState<string>("");
  const [textColumn, setTextColumn] = useState("");
  const [ratingColumn, setRatingColumn] = useState("");
  const [step, setStep] = useState<"select" | "configure">("select");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [customCategories, setCustomCategories] = useState<{ name: string; keywords: string }[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped && /\.(csv|xlsx|xls|json)$/i.test(dropped.name)) {
      setFile(dropped);
      setError("");
    } else {
      setError("Please upload a CSV, Excel, or JSON file");
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setError("");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      setAnalysisId(data.analysis_id);
      setColumns(data.columns);
      setRowCount(data.row_count);
      setPreview(data.preview);
      setFilename(data.filename);

      const autoText = data.columns.find((c: string) =>
        /review|text|comment|feedback|content/i.test(c)
      );
      const autoRating = data.columns.find((c: string) =>
        /rating|score|star|rank/i.test(c)
      );
      if (autoText) setTextColumn(autoText);
      if (autoRating) setRatingColumn(autoRating);

      setStep("configure");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = () => {
    if (!textColumn) {
      setError("Please select a text column");
      return;
    }
    const cats: Record<string, string[]> = {};
    customCategories.forEach((c) => {
      if (c.name && c.keywords) {
        cats[c.name.toLowerCase().replace(/\s+/g, "_")] = c.keywords.split(",").map((k) => k.trim().toLowerCase());
      }
    });
    onUploadComplete({
      analysisId,
      columns,
      rowCount,
      preview,
      filename,
      textColumn,
      ratingColumn,
      customCategories: Object.keys(cats).length > 0 ? cats : undefined,
    });
  };

  const addCategory = () => setCustomCategories([...customCategories, { name: "", keywords: "" }]);
  const removeCategory = (i: number) => setCustomCategories(customCategories.filter((_, idx) => idx !== i));
  const updateCategory = (i: number, field: "name" | "keywords", val: string) => {
    const updated = [...customCategories];
    updated[i][field] = val;
    setCustomCategories(updated);
  };

  const activeStep = step === "select" ? 0 : 1;

  return (
    <div className="fx-page">
      <div className="page-3d" aria-hidden="true">
        <div className="geo geo-ring" />
        <div className="geo geo-wave" />
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="grid-floor" />
      </div>

      <div className="fx-content">
        <div className="page-title-block">
          <span className="hero-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>Upload Your Dataset</span>
          </span>
          <h1 className="page-title">
            Turn reviews into insights in <span className="hero-title-gradient">3 steps</span>
          </h1>
          <p className="page-subtitle">
            Drop a CSV, Excel, or JSON collection of reviews. AnZlyze auto-detects your columns and runs the full ML pipeline.
          </p>
        </div>

        {/* Stepper */}
        <div className="stepper">
          {STEPS.map((s, i) => (
            <div key={s} className={`stepper-step ${i <= activeStep ? "active" : ""}`}>
              <span className="stepper-dot">{i + 1}</span>
              <span className="stepper-label">{s}</span>
            </div>
          ))}
        </div>

        <div className="upload-container">
          {step === "select" && (
            <div
              className="dropzone dropzone-premium"
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.xlsx,.xls,.json"
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
              <div className="dropzone-orb">
                <div className="dropzone-orbit dropzone-orbit-a" />
                <div className="dropzone-orbit dropzone-orbit-b" />
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <h3 className="dropzone-title">Drag &amp; drop your file here</h3>
              <p className="dropzone-sub">or click to browse from your computer</p>

              {file ? (
                <div className="file-selected">
                  <span className="file-check">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </span>
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
                </div>
              ) : (
                <div className="format-chips">
                  {SUPPORTED.map((f) => (
                    <span key={f} className="format-chip">{f}</span>
                  ))}
                </div>
              )}

              {file && (
                <div className="dropzone-actions">
                  <button
                    className="btn btn-primary"
                    onClick={(e) => { e.stopPropagation(); handleUpload(); }}
                    disabled={uploading}
                  >
                    {uploading ? "Uploading..." : "Upload & Preview"}
                  </button>
                  <button
                    className="btn btn-ghost"
                    onClick={(e) => { e.stopPropagation(); setFile(null); fileRef.current?.click(); }}
                  >
                    Choose another
                  </button>
                </div>
              )}
            </div>
          )}

          {step === "configure" && (
            <div className="config-panel">
              <div className="config-head">
                <div>
                  <h3 className="config-title">Configure Analysis</h3>
                  <p className="config-subtitle">
                    Tell AnZlyze which columns power the insights
                  </p>
                </div>
                <div className="config-chips">
                  <span className="config-chip"><strong>{rowCount}</strong> rows</span>
                  <span className="config-chip"><strong>{columns.length}</strong> columns</span>
                  <span className="config-chip config-chip-file">{filename}</span>
                </div>
              </div>

              <div className="config-table-wrapper">
                <table className="preview-table">
                  <thead>
                    <tr>
                      {columns.map((col) => (
                        <th key={col}>
                          {col}
                          {/review|text|comment|feedback|content/i.test(col) && <span className="col-type col-type-text">text</span>}
                          {/rating|score|star|rank/i.test(col) && <span className="col-type col-type-rating">rating</span>}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.map((row, i) => (
                      <tr key={i}>
                        {columns.map((col) => (
                          <td key={col}>{String(row[col] ?? "").slice(0, 60)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="config-fields">
                <div className="config-field">
                  <label>
                    Review Text Column *
                    <span className="field-badge field-badge-required">required</span>
                  </label>
                  <select value={textColumn} onChange={(e) => setTextColumn(e.target.value)}>
                    <option value="">Select column...</option>
                    {columns.map((col) => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                  <p className="field-hint">The actual review comments — this is what the ML models analyze.</p>
                </div>
                <div className="config-field">
                  <label>
                    Rating Column
                    <span className="field-badge field-badge-optional">optional</span>
                  </label>
                  <select value={ratingColumn} onChange={(e) => setRatingColumn(e.target.value)}>
                    <option value="">None — auto-derive from text</option>
                    {columns.map((col) => (
                      <option key={col} value={col}>{col}</option>
                    ))}
                  </select>
                  <p className="field-hint">Star / numeric ratings, used as ground truth to measure model accuracy.</p>
                </div>
              </div>

              <div className="custom-categories-section">
                <h4>Custom Problem Categories (optional)</h4>
                {customCategories.map((cat, i) => (
                  <div key={i} className="category-row">
                    <input
                      type="text"
                      placeholder="Category name"
                      value={cat.name}
                      onChange={(e) => updateCategory(i, "name", e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Keywords (comma-separated)"
                      value={cat.keywords}
                      onChange={(e) => updateCategory(i, "keywords", e.target.value)}
                    />
                    <button className="btn-icon" onClick={() => removeCategory(i)}>x</button>
                  </div>
                ))}
                <button className="btn btn-secondary btn-sm" onClick={addCategory}>+ Add Category</button>
              </div>
            </div>
          )}

          {error && <div className="error-msg">{error}</div>}

          <div className="upload-actions">
            {step === "configure" && (
              <button className="btn btn-ghost" onClick={() => { setStep("select"); setFile(null); }}>
                &#8592; Back
              </button>
            )}
            {step === "configure" && (
              <button className="btn btn-primary btn-lg" onClick={handleAnalyze} disabled={!textColumn}>
                Start Analysis &#8594;
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}