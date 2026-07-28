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

const MIN_SIZE = 12;
const MAX_SIZE = 48;

export default function WordCloud({ analysisId }: Props) {
  const [words, setWords] = useState<WordFreq[]>([]);
  const [active, setActive] = useState<string>("all");

  useEffect(() => {
    getWordFrequency(analysisId)
      .then((res) => setWords(res.words.slice(0, 80)))
      .catch(() => {});
  }, [analysisId]);

  const maxCount = useMemo(() => Math.max(...words.map((w) => w.total), 1), [words]);

  const filtered = useMemo(() => {
    if (active === "all") return words;
    return words.filter((w) => {
      const val = w[active as keyof WordFreq];
      return typeof val === "number" && val > 0;
    }).map((w) => {
      const total = (w.positive + w.negative + w.neutral) || 1;
      const pct = w[active as keyof WordFreq] as number;
      return { ...w, _relevance: pct / total };
    }).sort((a, b) => (b._relevance || 0) - (a._relevance || 0));
  }, [words, active]);

  const getWordColor = (w: WordFreq): string => {
    if (active !== "all") return SENTIMENT_COLORS[active];
    const max = Math.max(w.positive, w.negative, w.neutral);
    if (max === w.negative && w.negative > 0) return SENTIMENT_COLORS.negative;
    if (max === w.positive && w.positive > 0) return SENTIMENT_COLORS.positive;
    return SENTIMENT_COLORS.neutral;
  };

  if (words.length === 0) return null;

  const tabs = ["all", "positive", "negative", "neutral"];

  return (
    <div className="insight-card">
      <h3>Word Cloud</h3>
      <div className="wordcloud-tabs">
        {tabs.map((t) => (
          <button
            key={t}
            className={`wordcloud-tab ${active === t ? "active" : ""}`}
            onClick={() => setActive(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      <div className="wordcloud">
        {filtered.map((w) => {
          const ratio = w.total / maxCount;
          const size = MIN_SIZE + ratio * (MAX_SIZE - MIN_SIZE);
          const color = getWordColor(w);
          return (
            <span
              key={w.word}
              className="wordcloud-word"
              style={{ fontSize: `${size}px`, color, opacity: 0.3 + ratio * 0.7 }}
              title={`${w.word} — Total: ${w.total}, Positive: ${w.positive}, Negative: ${w.negative}, Neutral: ${w.neutral}`}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </div>
  );
}
