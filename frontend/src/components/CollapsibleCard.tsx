import { useState, useRef, useEffect, type ReactNode } from "react";

interface Props {
  title: string;
  subtitle?: string;
  badge?: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

export default function CollapsibleCard({ title, subtitle, badge, children, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | "auto">(defaultOpen ? "auto" : 0);

  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    if (open) {
      setHeight(el.scrollHeight);
      const t = setTimeout(() => setHeight("auto"), 200);
      return () => clearTimeout(t);
    } else {
      setHeight(el.scrollHeight);
      requestAnimationFrame(() => setHeight(0));
    }
  }, [open]);

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
      <div
        className="collapsible-body"
        style={{
          maxHeight: height === "auto" ? "none" : `${height}px`,
          overflow: "hidden",
          opacity: height === 0 ? 0 : 1,
          transition: "max-height 0.25s ease, opacity 0.2s ease",
        }}
      >
        <div ref={bodyRef}>{children}</div>
      </div>
    </div>
  );
}
