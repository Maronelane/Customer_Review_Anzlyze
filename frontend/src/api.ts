const API_BASE = "/api";

function getToken(): string | null {
  try {
    const saved = localStorage.getItem("auth");
    if (saved) return JSON.parse(saved).token;
  } catch { /* ignore */ }
  return null;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options?.headers) {
    Object.assign(headers, options.headers);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "API request failed");
  }
  return res.json();
}

export interface UploadResponse {
  analysis_id: string;
  filename: string;
  columns: string[];
  row_count: number;
  preview: Record<string, unknown>[];
  stored_path: string;
}

export interface AnalyzeResponse {
  analysis_id: string;
  status: string;
  best_model: string;
  best_accuracy: number;
  sentiment_distribution: {
    positive: number;
    negative: number;
    neutral: number;
    total: number;
  };
  problem_count: number;
  total_recommendations: number;
}

export interface Problem {
  category: string;
  category_key: string;
  frequency: number;
  severity: string;
  percentage: number;
  examples: string[];
  is_custom?: boolean;
}

export interface Recommendation {
  title: string;
  priority: string;
  problem_category: string;
  problem_frequency: number;
  problem_percentage: number;
  suggestions: string[];
  impact: string;
  examples: string[];
}

export interface ResultsData {
  analysis: {
    id: string;
    filename: string;
    text_column: string;
    rating_column: string | null;
    total_reviews: number;
    status: string;
    created_at: string;
  };
  results: {
    best_model: string;
    best_accuracy: number;
    sentiment_distribution: {
      positive: number;
      negative: number;
      neutral: number;
      total: number;
    };
    problems: {
      problems: Problem[];
      total_negative: number;
      top_complaint_words: { word: string; count: number }[];
    };
    recommendations: {
      recommendations: Recommendation[];
      summary: string;
      overall_sentiment: string;
      total_recommendations: number;
    };
    model_results: Record<string, { accuracy: number; report: unknown }>;
  };
}

export interface Prediction {
  id: number;
  analysis_id: string;
  review_text: string;
  sentiment: string;
}

export interface PredictionResponse {
  predictions: Prediction[];
  total: number;
}

export interface Analysis {
  id: string;
  filename: string;
  text_column: string;
  rating_column: string | null;
  total_reviews: number | null;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface ProgressData {
  step: string;
  percent: number;
}

export function uploadDataset(file: File, textColumn: string, ratingColumn: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (textColumn) formData.append("text_column", textColumn);
  if (ratingColumn) formData.append("rating_column", ratingColumn);

  return apiFetch<UploadResponse>("/upload", {
    method: "POST",
    body: formData,
  });
}

export function runAnalysis(analysisId: string, textColumn: string, ratingColumn: string, customCategories?: Record<string, string[]>, useTransformer?: boolean) {
  return apiFetch<AnalyzeResponse>("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      analysis_id: analysisId,
      text_column: textColumn,
      rating_column: ratingColumn,
      custom_categories: customCategories || null,
      use_transformer: useTransformer || false,
    }),
  });
}

export function getResults(analysisId: string) {
  return apiFetch<ResultsData>(`/results/${analysisId}`);
}

export function getPredictions(
  analysisId: string,
  limit = 50,
  offset = 0,
  sentiment?: string,
  search?: string
) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (sentiment) params.set("sentiment", sentiment);
  if (search) params.set("q", search);
  return apiFetch<PredictionResponse>(`/predictions/${analysisId}?${params}`);
}

export function getProgress(analysisId: string) {
  return apiFetch<ProgressData>(`/progress/${analysisId}`);
}

export function listAnalyses() {
  return apiFetch<Analysis[]>("/analyses");
}

export function rerunAnalysis(analysisId: string, textColumn?: string, ratingColumn?: string, customCategories?: Record<string, string[]>, useTransformer?: boolean) {
  return apiFetch<AnalyzeResponse>("/rerun", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      analysis_id: analysisId,
      text_column: textColumn,
      rating_column: ratingColumn,
      custom_categories: customCategories || null,
      use_transformer: useTransformer || false,
    }),
  });
}

export interface TrendPoint {
  date: string;
  positive: number;
  negative: number;
  neutral: number;
  total: number;
}

export function getTrend(analysisId: string) {
  return apiFetch<{ trend: TrendPoint[]; message: string | null }>(`/trend/${analysisId}`);
}

export interface WordFreq {
  word: string;
  total: number;
  positive: number;
  negative: number;
  neutral: number;
}

export function getWordFrequency(analysisId: string) {
  return apiFetch<{ words: WordFreq[] }>(`/word-frequency/${analysisId}`);
}

export function getAiSummary(analysisId: string) {
  return apiFetch<{ summary: string }>(`/summary/${analysisId}`);
}
