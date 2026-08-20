import { useState, useEffect, useMemo } from "react";
import { getWordFrequency, type WordFreq } from "../api";

interface Props {
  analysisId: string;
}

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#22c55e",
  negative: "#ef4444",
  neutral: "#f59e0b",
};

const MIN_SIZE = 13;
const MAX_SIZE = 42;

function seededRandom(seed: number) {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

export default function WordCloud({ analysisId }: Props) {
  const [words, setWords] = useState<WordFreq[]>([]);
  const [active, setActive] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getWordFrequency(analysisId)
      .then((res) => setWords(res.words?.slice(0, 80) || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [analysisId]);

  const maxCount = useMemo(() => Math.max(...words.map((w) => w.total), 1), [words]);

  const filtered = useMemo(() => {
    if (active === "all") return words;
    return words
      .filter((w) => {
        const val = w[active as keyof WordFreq];
        return typeof val === "number" && val > 0;
      })
      .map((w) => {
        const total = (w.positive + w.negative + w.neutral) || 1;
        const pct = w[active as keyof WordFreq] as number;
        return { ...w, _relevance: pct / total };
      })
      .sort((a, b) => (b._relevance || 0) - (a._relevance || 0));
  }, [words, active]);

  const getWordColor = (w: WordFreq): string => {
    if (active !== "all") return SENTIMENT_COLORS[active];
    const max = Math.max(w.positive, w.negative, w.neutral);
    if (max === w.negative && w.negative > 0) return SENTIMENT_COLORS.negative;
    if (max === w.positive && w.positive > 0) return SENTIMENT_COLORS.positive;
    return SENTIMENT_COLORS.neutral;
  };

  if (loading) {
    return (
      <div className="wordcloud-loading">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '12px 0' }}>
          <div className="skeleton skeleton-text short" />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            {[...Array(12)].map((_, i) => (
              <div key={i} className="skeleton skeleton-text" style={{ width: 40 + Math.random() * 80, height: 16 }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (words.length === 0) {
    return <div className="wordcloud-empty" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ opacity: 0.5 }}>
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <p>No word frequency data available.</p>
    </div>;
  }

  const tabs = ["all", "positive", "negative", "neutral"];

  return (
    <>
      <div className="wordcloud-header">
        <h3>Word Cloud</h3>
        <span className="wordcloud-count">{filtered.length} words</span>
      </div>
      <div className="wordcloud-tabs">
        {tabs.map((t) => (
          <button
            key={t}
            className={`wordcloud-tab ${active === t ? "active" : ""}`}
            onClick={() => setActive(t)}
          >
            {t === "all" && "All"}
            {t === "positive" && "Positive"}
            {t === "negative" && "Negative"}
            {t === "neutral" && "Neutral"}
          </button>
        ))}
      </div>
      <div className="wordcloud">
        {filtered.map((w, idx) => {
          const ratio = w.total / maxCount;
          const size = MIN_SIZE + ratio * (MAX_SIZE - MIN_SIZE);
          const color = getWordColor(w);
          const rotation = seededRandom(idx) > 0.7 ? (seededRandom(idx + 50) > 0.5 ? 8 : -8) : 0;
          const fontWeight = ratio > 0.5 ? 800 : ratio > 0.25 ? 600 : 400;
          return (
            <span
              key={w.word}
              className="wordcloud-word"
              style={{
                fontSize: `${size}px`,
                color,
                opacity: 0.35 + ratio * 0.65,
                fontWeight,
                transform: `rotate(${rotation}deg)`,
              }}
              title={`${w.word}\nTotal: ${w.total}  |  Positive: ${w.positive}  |  Negative: ${w.negative}  |  Neutral: ${w.neutral}`}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </>
  );
}
