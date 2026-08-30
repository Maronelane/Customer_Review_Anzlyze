import { useState, useRef, useEffect } from "react";

interface Props {
  analysisId: string;
}

export default function ExportButton({ analysisId }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const handleExport = (format: string) => {
    window.open(`/api/export/${analysisId}?format=${format}`, "_blank");
    setOpen(false);
  };

  return (
    <div className="export-wrapper" ref={ref}>
      <button className="btn btn-secondary action-btn" onClick={() => setOpen(!open)}>
        <svg className="btn-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3v12" /><path d="m8 11 4 4 4-4" /><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
        </svg>
        Export
        <svg className="btn-caret" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div className="dropdown-menu premium">
          <button className="drop-item" onClick={() => handleExport("excel")}>
            <span className="drop-icon xlsx">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="3" y="3" width="18" height="18" rx="3" />
                <path d="M9 8l6 8M15 8l-6 8" />
              </svg>
            </span>
            <span className="drop-text">
              <span className="drop-title">Excel Report</span>
              <span className="drop-desc">Formatted workbook with charts &amp; all sheets</span>
            </span>
          </button>
          <button className="drop-item" onClick={() => handleExport("pdf")}>
            <span className="drop-icon pdf">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M14 3v4a1 1 0 0 0 1 1h4" />
                <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z" />
                <path d="M9 13h6M9 16h4" />
              </svg>
            </span>
            <span className="drop-text">
              <span className="drop-title">PDF Report</span>
              <span className="drop-desc">Presentation-ready executive document</span>
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
