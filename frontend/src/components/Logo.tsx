export default function Logo() {
  return (
    <div className="logo">
      <span className="logo-mark" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          <path d="M8.5 9.5h7M8.5 13h4.5" />
        </svg>
        <span className="logo-live" />
      </span>
      <span className="logo-text">
        <span className="logo-word">AnZlyze</span>
        <span className="logo-tag">review intelligence</span>
      </span>
    </div>
  );
}