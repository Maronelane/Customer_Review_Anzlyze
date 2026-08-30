import { useState, useEffect, useRef } from "react";
import { getPredictions, type Prediction, type PredictionResponse } from "../api";

interface Props {
  analysisId: string;
  activeModel?: string;
}

const LIMIT = 20;
const DEBOUNCE_MS = 250;
const SNIPPET_LEN = 220;

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Build a case-insensitive regex that highlights each search term
 *  (word-boundary prefix so partial matches like "batt"→"battery" show). */
function buildSearchRegex(query: string): RegExp | null {
  const trimmed = query.trim();
  if (!trimmed) return null;
  const terms = trimmed.split(/\s+/).filter(Boolean);
  const parts = terms.map((t) => {
    const esc = escapeRegExp(t);
    if (/^[A-Za-z0-9_]+$/.test(t) && t.length >= 2) return `\\b${esc}`;
    if (/^[A-Za-z0-9_]+$/.test(t)) return `\\b${esc}\\b`;
    return esc;
  });
  return new RegExp(`(?:${parts.join("|")})`, "gi");
}

/** Slice a snippet of ~SNIPPET_LEN chars centred on the first match. */
function extractSnippet(text: string, regex: RegExp): string {
  regex.lastIndex = 0;
  const m = regex.exec(text);
  if (!m) return text.slice(0, SNIPPET_LEN);
  const head = Math.floor(SNIPPET_LEN * 0.35);
  let start = Math.max(0, m.index - head);
  let end = Math.min(text.length, start + SNIPPET_LEN);
  if (end - start < SNIPPET_LEN) start = Math.max(0, end - SNIPPET_LEN);
  const prefix = start > 0 ? "…" : "";
  const suffix = end < text.length ? "…" : "";
  return prefix + text.slice(start, end) + suffix;
}

/** Render review text, wrapping every query match in a <mark>. */
function HighlightedText({ text, regex }: { text: string; regex: RegExp | null }) {
  if (!regex) {
    return (
      <span className="review-text">
        {text.length > SNIPPET_LEN ? text.slice(0, SNIPPET_LEN) + "…" : text}
      </span>
    );
  }
  const snippet = extractSnippet(text, regex);
  const hl = new RegExp(regex.source, "gi");
  const nodes: (string | JSX.Element)[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = hl.exec(snippet)) !== null) {
    if (m[0].length === 0) {
      hl.lastIndex++;
      continue;
    }
    nodes.push(snippet.slice(last, m.index));
    nodes.push(
      <mark key={m.index} className="search-highlight">
        {m[0]}
      </mark>,
    );
    last = m.index + m[0].length;
  }
  nodes.push(snippet.slice(last));
  return <span className="review-text">{nodes}</span>;
}

export default function ReviewTable({ analysisId, activeModel }: Props) {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<string>("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const fetchPredictions = async () => {
    setLoading(true);
    try {
      const data: PredictionResponse = await getPredictions(
        analysisId, LIMIT, page * LIMIT, filter || undefined, search || undefined, activeModel
      );
      setPredictions(data.predictions);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(0);
  }, [filter, search, activeModel]);

  useEffect(() => {
    fetchPredictions();
  }, [analysisId, page, filter, search, activeModel]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const handleSearch = (val: string) => {
    setSearchInput(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setSearch(val), DEBOUNCE_MS);
  };

  const totalPages = Math.ceil(total / LIMIT);
  const searchRegex = buildSearchRegex(search);

  const sentimentColor = (s: string) => {
    if (s === "positive") return "#22c55e";
    if (s === "negative") return "#ef4444";
    return "#f59e0b";
  };

  return (
    <div className="card review-table-card">
      <div className="card-header">
        <h3>Review Predictions</h3>
        <div className="table-controls">
          <input
            type="text"
            className="search-input"
            placeholder="Search reviews..."
            value={searchInput}
            onChange={(e) => handleSearch(e.target.value)}
          />
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All Sentiments</option>
            <option value="positive">Positive Only</option>
            <option value="negative">Negative Only</option>
            <option value="neutral">Neutral Only</option>
          </select>
          <span className="total-count">{total} reviews</span>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="reviews-table">
          <thead>
            <tr>
              <th className="col-num">#</th>
              <th className="col-text">Review Text</th>
              <th className="col-sentiment">Sentiment</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={3} className="loading-cell">Loading...</td>
              </tr>
            ) : predictions.length === 0 ? (
              <tr>
                <td colSpan={3} className="loading-cell">
                  {search ? "No reviews matched your search" : "No predictions found"}
                </td>
              </tr>
            ) : (
              predictions.map((p, i) => (
                <tr key={p.id}>
                  <td className="col-num">{page * LIMIT + i + 1}</td>
                  <td className="col-text">
                    <HighlightedText text={p.review_text} regex={searchRegex} />
                  </td>
                  <td className="col-sentiment">
                    <span
                      className="sentiment-badge"
                      style={{ backgroundColor: sentimentColor(p.sentiment) }}
                    >
                      {p.sentiment}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button disabled={page === 0} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <button disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}