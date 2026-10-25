/**
 * src/api/client.ts
 * Type-safe API client for WindScope backend.
 */

import {
  AccuracySummaryResponse,
  DecisionForecastResponse,
  DiurnalResponse,
  DistributionResponse,
  ForecastSeriesResponse,
  HealthResponse,
  ReadyResponse,
} from "./types";

const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export function getBaseUrl(): string {
  // 1. Explicit environment configuration takes highest precedence (e.g. Vercel build)
  if (RAW_API_BASE_URL && RAW_API_BASE_URL.trim() !== "") {
    return RAW_API_BASE_URL.trim().replace(/\/+$/, "");
  }

  // 2. Browser context:
  if (typeof window !== "undefined" && window.location?.origin) {
    // In local Vite development mode without explicit VITE_API_BASE_URL, default to localhost:8000
    if (import.meta.env.DEV) {
      return "http://localhost:8000";
    }
    // In Docker Compose / same-origin container deployment, use current window origin
    return window.location.origin.replace(/\/+$/, "");
  }

  // 3. Fallback for non-browser / test environments
  return "http://localhost:8000";
}

export class ApiError extends Error {
  status: number;
  errorCode?: string;

  constructor(status: number, message: string, errorCode?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

export interface TimedResponse<T> {
  data: T;
  latencyMs: number;
  timestamp: Date;
}

async function request<T>(endpoint: string, params?: Record<string, string>, signal?: AbortSignal): Promise<TimedResponse<T>> {
  const base = getBaseUrl();
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  const url = new URL(cleanEndpoint, base);
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        url.searchParams.append(key, val);
      }
    });
  }

  const start = performance.now();
  let res: Response;
  try {
    res = await fetch(url.toString(), {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      signal,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw err;
    }
    throw new ApiError(0, `Network error connecting to API: ${err instanceof Error ? err.message : String(err)}`);
  }

  const latencyMs = Math.round(performance.now() - start);

  if (!res.ok) {
    let errMsg = `HTTP ${res.status}: ${res.statusText}`;
    let errorCode: string | undefined;
    try {
      const errBody = await res.json();
      if (errBody.message) errMsg = errBody.message;
      if (errBody.error_code) errorCode = errBody.error_code;
    } catch {
      // Body not JSON
    }
    throw new ApiError(res.status, errMsg, errorCode);
  }

  const data: T = await res.json();
  return {
    data,
    latencyMs,
    timestamp: new Date(),
  };
}

export const api = {
  getHealth: (signal?: AbortSignal) =>
    request<HealthResponse>("/api/v1/health", undefined, signal),

  getReady: (signal?: AbortSignal) =>
    request<ReadyResponse>("/api/v1/ready", undefined, signal),

  getDecisionForecast: (decisionDate: string, cutoff: string = "10:00:00", signal?: AbortSignal) =>
    request<DecisionForecastResponse>(
      "/api/v1/decisions/forecast",
      { decision_date: decisionDate, cutoff },
      signal
    ),

  getForecastSeries: (
    decisionDateFrom: string = "2026-01-01",
    decisionDateTo: string = "2026-01-31",
    cutoff: string = "10:00:00",
    signal?: AbortSignal
  ) =>
    request<ForecastSeriesResponse>(
      "/api/v1/forecasts/series",
      { decision_date_from: decisionDateFrom, decision_date_to: decisionDateTo, cutoff },
      signal
    ),

  getAccuracySummary: (
    decisionDateFrom: string = "2026-01-01",
    decisionDateTo: string = "2026-01-31",
    cutoff: string = "10:00:00",
    signal?: AbortSignal
  ) =>
    request<AccuracySummaryResponse>(
      "/api/v1/accuracy/summary",
      { decision_date_from: decisionDateFrom, decision_date_to: decisionDateTo, cutoff },
      signal
    ),

  getAccuracyDiurnal: (
    decisionDateFrom: string = "2026-01-01",
    decisionDateTo: string = "2026-01-31",
    cutoff: string = "10:00:00",
    signal?: AbortSignal
  ) =>
    request<DiurnalResponse>(
      "/api/v1/accuracy/diurnal",
      { decision_date_from: decisionDateFrom, decision_date_to: decisionDateTo, cutoff },
      signal
    ),

  getAccuracyDistribution: (
    decisionDateFrom: string = "2026-01-01",
    decisionDateTo: string = "2026-01-31",
    cutoff: string = "10:00:00",
    signal?: AbortSignal
  ) =>
    request<DistributionResponse>(
      "/api/v1/accuracy/distribution",
      { decision_date_from: decisionDateFrom, decision_date_to: decisionDateTo, cutoff },
      signal
    ),
};
