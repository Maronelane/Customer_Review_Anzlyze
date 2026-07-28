import { useState } from "react";

interface Props {
  analysisId: string;
}

export default function ExportButton({ analysisId }: Props) {
  const [open, setOpen] = useState(false);

  const handleExport = (format: string) => {
    window.open(`/api/export/${analysisId}?format=${format}`, "_blank");
    setOpen(false);
  };

  return (
    <div className="export-wrapper">
      <button className="btn btn-secondary" onClick={() => setOpen(!open)}>
        Export
      </button>
      {open && (
        <div className="dropdown-menu">
          <button onClick={() => handleExport("excel")}>Export as Excel</button>
          <button onClick={() => handleExport("pdf")}>Export as PDF</button>
        </div>
      )}
    </div>
  );
}
