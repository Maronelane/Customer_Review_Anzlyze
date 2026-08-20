import { useState, type ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  badge?: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

export default function CollapsibleCard({ title, subtitle, badge, children, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`collapsible-card ${open ? "open" : "closed"}`}>
      <button className="collapsible-header" onClick={() => setOpen(!open)}>
        <div className="collapsible-header-left">
          <h3>{title}</h3>
          {subtitle && <span className="collapsible-subtitle">{subtitle}</span>}
        </div>
        <div className="collapsible-header-right">
          {badge && <span className="collapsible-badge">{badge}</span>}
          <span className={`collapsible-chevron ${open ? "open" : ""}`}>&#9662;</span>
        </div>
      </button>
      {open && <div className="collapsible-body">{children}</div>}
    </div>
  );
}
