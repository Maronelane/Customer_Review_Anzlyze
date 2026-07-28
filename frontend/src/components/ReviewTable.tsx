import { useState, useEffect, useRef } from "react";
import { getPredictions, type Prediction, type PredictionResponse } from "../api";

interface Props {
  analysisId: string;
}

export default function ReviewTable({ analysisId }: Props) {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const searchRef = useRef<ReturnType<typeof setTimeout>>();
  const limit = 20;

  const fetchPredictions = async () => {
    setLoading(true);
    try {
      const data: PredictionResponse = await getPredictions(
        analysisId, limit, page * limit, filter || undefined, search || undefined
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
  }, [filter, search]);

  useEffect(() => {
    fetchPredictions();
  }, [analysisId, page, filter, search]);

  const handleSearch = (val: string) => {
    setSearch(val);
    if (searchRef.current) clearTimeout(searchRef.current);
    searchRef.current = setTimeout(() => {}, 300);
  };

  const totalPages = Math.ceil(total / limit);

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
            value={search}
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
                <td colSpan={3} className="loading-cell">No predictions found</td>
              </tr>
            ) : (
              predictions.map((p, i) => (
                <tr key={p.id}>
                  <td className="col-num">{page * limit + i + 1}</td>
                  <td className="col-text">
                    <span className="review-text">{p.review_text.slice(0, 200)}</span>
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
