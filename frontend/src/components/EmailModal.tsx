import { useState } from "react";

interface Props {
  analysisId: string;
  onClose: () => void;
}

type Format = "pdf" | "excel";

export default function EmailModal({ analysisId, onClose }: Props) {
  const [email, setEmail] = useState("");
  const [formats, setFormats] = useState<Format[]>(["pdf", "excel"]);
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");

  const toggleFormat = (f: Format) => {
    setFormats((prev) => {
      if (prev.includes(f)) return prev.length > 1 ? prev.filter((x) => x !== f) : prev;
      return [...prev, f];
    });
  };

  const handleSend = async () => {
    if (!email) return;
    setStatus("sending");
    setError("");
    try {
      const res = await fetch("/api/email-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, analysis_id: analysisId, formats }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setStatus("sent");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send");
      setStatus("error");
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content email-modal" onClick={(e) => e.stopPropagation()}>
        <div className="email-head">
          <div className="email-head-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="3" />
              <path d="m4 6 8 6 8-6" />
            </svg>
          </div>
          <div className="email-head-text">
            <h3>Share Report</h3>
            <p>Email the analysis with branded attachments</p>
          </div>
        </div>

        {status === "sent" ? (
          <div className="modal-success email-success">
            <div className="success-ring">
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="m5 13 4 4L19 7" />
              </svg>
            </div>
            <h3>Report sent!</h3>
            <p>Delivered to <strong>{email}</strong> with the attachments you selected.</p>
            <button className="btn btn-primary" onClick={onClose}>Done</button>
          </div>
        ) : (
          <>
            <div className="auth-field">
              <label>Recipient Email</label>
              <div className="field-input-wrap">
                <svg className="field-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="2" y="4" width="20" height="16" rx="3" />
                  <path d="m4 6 8 6 8-6" />
                </svg>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="recipient@company.com"
                />
              </div>
            </div>

            <div className="email-attach">
              <span className="attach-label">Include attachments</span>
              <div className="attach-grid">
                <button
                  className={`attach-card ${formats.includes("pdf") ? "on" : ""}`}
                  onClick={() => toggleFormat("pdf")}
                  type="button"
                >
                  <span className="attach-chip pdf">PDF</span>
                  <span className="attach-name">PDF Report</span>
                  <span className={formats.includes("pdf") ? "check on" : "check"}>✓</span>
                </button>
                <button
                  className={`attach-card ${formats.includes("excel") ? "on" : ""}`}
                  onClick={() => toggleFormat("excel")}
                  type="button"
                >
                  <span className="attach-chip xlsx">XLSX</span>
                  <span className="attach-name">Excel Workbook</span>
                  <span className={formats.includes("excel") ? "check on" : "check"}>✓</span>
                </button>
              </div>
            </div>

            {error && <div className="error-msg">{error}</div>}

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={onClose} disabled={status === "sending"}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSend} disabled={status === "sending" || !email}>
                {status === "sending" ? (
                  <>
                    <span className="btn-spinner" /> Sending...
                  </>
                ) : "Send Report"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
