import type {
  MovementDetail,
  MovementSwingsResponse,
  PatternReport,
  RecordsResponse,
  SummaryResponse
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
const API_KEY = import.meta.env.VITE_API_KEY;

type Filters = {
  clubs: string[];
  ratings: number[];
};

const buildParams = (filters: Filters): string => {
  const params = new URLSearchParams();
  filters.clubs.forEach((club) => params.append("clubs", club));
  filters.ratings.forEach((rating) => params.append("ratings", String(rating)));
  return params.toString();
};

export const fetchSummary = async (filters: Filters): Promise<SummaryResponse> => {
  const query = buildParams(filters);
  const response = await fetch(`${API_BASE}/summary${query ? `?${query}` : ""}`, {
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined
  });
  if (!response.ok) {
    throw new Error(`Failed to load summary (${response.status})`);
  }
  return (await response.json()) as SummaryResponse;
};

export const fetchRecords = async (
  filters: Filters,
  limit = 500
): Promise<RecordsResponse> => {
  const query = buildParams(filters);
  const suffix = query ? `${query}&limit=${limit}` : `limit=${limit}`;
  const response = await fetch(`${API_BASE}/records?${suffix}`, {
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined
  });
  if (!response.ok) {
    throw new Error(`Failed to load records (${response.status})`);
  }
  return (await response.json()) as RecordsResponse;
};

export const fetchMovementSwings = async (): Promise<MovementSwingsResponse> => {
  const response = await fetch(`${API_BASE}/movement/swings`, {
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined
  });
  if (!response.ok) {
    throw new Error(`Failed to load movement swings (${response.status})`);
  }
  return (await response.json()) as MovementSwingsResponse;
};

export const fetchMovementDetail = async (swingId: string): Promise<MovementDetail> => {
  const response = await fetch(`${API_BASE}/movement/${encodeURIComponent(swingId)}`, {
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined
  });
  if (!response.ok) {
    throw new Error(`Failed to load movement detail (${response.status})`);
  }
  return (await response.json()) as MovementDetail;
};

export const fetchPatterns = async (
  filters: Filters,
  options?: { llm?: boolean }
): Promise<PatternReport> => {
  const params = new URLSearchParams();
  filters.clubs.forEach((club) => params.append("clubs", club));
  filters.ratings.forEach((rating) => params.append("ratings", String(rating)));
  if (options?.llm) {
    params.append("llm", "true");
  }
  const query = params.toString();
  const response = await fetch(`${API_BASE}/patterns${query ? `?${query}` : ""}`, {
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined
  });
  if (!response.ok) {
    throw new Error(`Failed to load pattern report (${response.status})`);
  }
  return (await response.json()) as PatternReport;
};
