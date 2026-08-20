import { useState, useEffect } from "react";
import { getClusters, getClusterReviews, type ClusterData, type ClusterSummary, type Prediction } from "../api";

interface Props {
  analysisId: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#22c55e",
};

const SEVERITY_BG: Record<string, string> = {
  high: "rgba(239,68,68,0.08)",
  medium: "rgba(245,158,11,0.08)",
  low: "rgba(34,197,94,0.08)",
};

export default function RootCauseClusters({ analysisId }: Props) {
  const [data, setData] = useState<ClusterData | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [reviews, setReviews] = useState<Prediction[]>([]);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getClusters(analysisId)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [analysisId]);

  useEffect(() => {
    if (selectedCluster === null) {
      setReviews([]);
      return;
    }
    setLoadingReviews(true);
    getClusterReviews(analysisId, selectedCluster)
      .then((res) => setReviews(res.reviews))
      .catch(() => {})
      .finally(() => setLoadingReviews(false));
  }, [analysisId, selectedCluster]);

  if (loading) {
    return <div className="cluster-loading">Loading clusters...</div>;
  }

  if (!data || data.clusters.length === 0) {
    return <p className="cluster-empty">No complaint clusters detected.</p>;
  }

  const selected = data.clusters.find((c) => c.cluster_id === selectedCluster);

  return (
    <>
      <p className="cluster-description">
        Similar complaints are grouped into root cause clusters. Click a cluster to see contributing reviews.
      </p>

      <div className="cluster-grid">
        {data.clusters.map((cluster) => (
          <button
            key={cluster.cluster_id}
            className={`cluster-tile ${selectedCluster === cluster.cluster_id ? "active" : ""}`}
            style={{
              borderLeftColor: SEVERITY_COLORS[cluster.severity],
              backgroundColor: selectedCluster === cluster.cluster_id
                ? SEVERITY_BG[cluster.severity]
                : undefined,
            }}
            onClick={() =>
              setSelectedCluster(
                selectedCluster === cluster.cluster_id ? null : cluster.cluster_id
              )
            }
          >
            <div className="cluster-tile-header">
              <span className="cluster-tile-label">{cluster.label}</span>
              <span
                className="cluster-severity-dot"
                style={{ backgroundColor: SEVERITY_COLORS[cluster.severity] }}
              />
            </div>
            <div className="cluster-tile-stats">
              <span>{cluster.count} reviews</span>
              <span>{cluster.negative_pct}% negative</span>
            </div>
            <div className="cluster-bar-bg">
              <div
                className="cluster-bar"
                style={{
                  width: `${cluster.negative_pct}%`,
                  backgroundColor: SEVERITY_COLORS[cluster.severity],
                }}
              />
            </div>
          </button>
        ))}
      </div>

      {selected && (
        <div className="cluster-detail">
          <div className="cluster-detail-header">
            <h4>{selected.label}</h4>
            <div className="cluster-detail-meta">
              <span className={`severity-badge ${selected.severity}`}>{selected.severity}</span>
              <span>{selected.count} reviews</span>
              <span>{selected.negative_pct}% negative</span>
            </div>
          </div>

          {selected.sample_reviews.length > 0 && (
            <div className="cluster-samples">
              <h5>Sample Complaints</h5>
              {selected.sample_reviews.map((review, i) => (
                <p key={i} className="cluster-sample-text">
                  &ldquo;{review.slice(0, 200)}&rdquo;
                </p>
              ))}
            </div>
          )}

          {loadingReviews ? (
            <p className="cluster-loading">Loading reviews...</p>
          ) : (
            reviews.length > 0 && (
              <div className="cluster-reviews">
                <h5>All Reviews in Cluster ({reviews.length})</h5>
                {reviews.slice(0, 15).map((r, i) => (
                  <div key={i} className="cluster-review-item">
                    <span
                      className="sentiment-dot"
                      style={{
                        backgroundColor:
                          r.sentiment === "positive" ? "#22c55e" :
                          r.sentiment === "negative" ? "#ef4444" : "#f59e0b",
                      }}
                    />
                    <p>{r.review_text.slice(0, 250)}</p>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}
    </>
  );
}
