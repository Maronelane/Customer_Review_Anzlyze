import React, { useState, useRef, useCallback } from "react";

interface Props {
  onUploadComplete: (data: {
    analysisId: string;
    columns: string[];
    rowCount: number;
    preview: Record<string, unknown>[];
    filename: string;
    customCategories?: Record<string, string[]>;
    useTransformer?: boolean;
  }) => void;
}

export default function FileUpload({ onUploadComplete }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [preview, setPreview] = useState<Record<string, unknown>[]>([]);
  const [rowCount, setRowCount] = useState(0);
  const [analysisId, setAnalysisId] = useState<string>("");
  const [filename, setFilename] = useState<string>("");
  const [textColumn, setTextColumn] = useState("");
  const [ratingColumn, setRatingColumn] = useState("");
  const [step, setStep] = useState<"select" | "configure" | "ready">("select");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [useTransformer, setUseTransformer] = useState(false);
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
      customCategories: Object.keys(cats).length > 0 ? cats : undefined,
      useTransformer,
    });
  };

  const addCategory = () => setCustomCategories([...customCategories, { name: "", keywords: "" }]);
  const removeCategory = (i: number) => setCustomCategories(customCategories.filter((_, idx) => idx !== i));
  const updateCategory = (i: number, field: "name" | "keywords", val: string) => {
    const updated = [...customCategories];
    updated[i][field] = val;
    setCustomCategories(updated);
  };

  return (
    <div className="upload-container">
      {step === "select" && (
        <div
          className="dropzone"
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
          <div className="dropzone-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <h3>Drop your file here</h3>
          <p>Supports CSV, Excel (.xlsx), and JSON files</p>
          {file && (
            <div className="file-selected">
              <span className="file-name">{file.name}</span>
              <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
            </div>
          )}
        </div>
      )}

      {step === "configure" && (
        <div className="config-panel">
          <h3>Configure Analysis</h3>
          <p className="config-subtitle">
            Detected <strong>{rowCount}</strong> reviews in <strong>{filename}</strong>
          </p>

          <div className="config-table-wrapper">
            <table className="preview-table">
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col}>{col}</th>
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
              <label>Review Text Column *</label>
              <select value={textColumn} onChange={(e) => setTextColumn(e.target.value)}>
                <option value="">Select column...</option>
                {columns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>
            <div className="config-field">
              <label>Rating Column (optional)</label>
              <select value={ratingColumn} onChange={(e) => setRatingColumn(e.target.value)}>
                <option value="">None</option>
                {columns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="advanced-options">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={useTransformer}
                onChange={(e) => setUseTransformer(e.target.checked)}
              />
              <span>Use Advanced Model (DistilBERT)</span>
              <span className="toggle-hint">Slower but more accurate</span>
            </label>
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
        {step === "select" && file && (
          <button className="btn btn-primary" onClick={handleUpload} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload & Preview"}
          </button>
        )}
        {step === "configure" && (
          <>
            <button className="btn btn-secondary" onClick={() => { setStep("select"); setFile(null); }}>
              Back
            </button>
            <button className="btn btn-primary" onClick={handleAnalyze} disabled={!textColumn}>
              Start Analysis
            </button>
          </>
        )}
      </div>
    </div>
  );
}
