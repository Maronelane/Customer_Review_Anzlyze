import { useState } from "react";

interface Props {
  analysisId: string;
  onClose: () => void;
}

export default function EmailModal({ analysisId, onClose }: Props) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");

  const handleSend = async () => {
    if (!email) return;
    setStatus("sending");
    try {
      const res = await fetch("/api/email-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, analysis_id: analysisId }),
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
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>Email Report</h3>
        {status === "sent" ? (
          <div className="modal-success">
            <p>Report sent successfully!</p>
            <button className="btn btn-primary" onClick={onClose}>Done</button>
          </div>
        ) : (
          <>
            <p className="modal-desc">Send the analysis report to an email address.</p>
            <div className="auth-field">
              <label>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="recipient@example.com"
              />
            </div>
            {error && <div className="error-msg">{error}</div>}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSend} disabled={status === "sending"}>
                {status === "sending" ? "Sending..." : "Send Report"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
