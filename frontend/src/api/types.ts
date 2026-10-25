/**
 * src/api/types.ts
 * TypeScript interfaces strictly matching FastAPI Pydantic response schemas.
 */

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface ReadyResponse {
  status: string;
  database: string;
  actual_observations_count: number;
  forecast_observations_count: number;
}

export interface ForecastDecisionItem {
  target_start_utc: string;
  delivery_hour_local: number;
  publish_time_utc: string | null;
  horizon_hours: number | null;
  forecast_generation_mw: number | null;
  actual_generation_mw: number | null;
  error_mw: number | null;
  absolute_error_mw: number | null;
  is_actual_complete: boolean;
  status: "MATCHED" | "MISSING_FORECAST" | "MISSING_ACTUAL" | string;
}

export interface DecisionForecastResponse {
  decision_date: string;
  delivery_date: string;
  cutoff_time: string;
  cutoff_timezone: string;
  cutoff_time_utc: string;
  total_hours: number;
  matched_hours: number;
  forecasts: ForecastDecisionItem[];
}

export interface SeriesDataPoint {
  target_start_utc: string;
  delivery_date: string;
  delivery_hour_local: number;
  publish_time_utc: string | null;
  forecast_mw: number | null;
  actual_mw: number | null;
  error_mw: number | null;
}

export interface ForecastSeriesResponse {
  decision_date_from: string;
  decision_date_to: string;
  delivery_date_from: string;
  delivery_date_to: string;
  cutoff_time: string;
  cutoff_timezone: string;
  total_points: number;
  matched_points: number;
  series: SeriesDataPoint[];
}

export interface CoverageStats {
  total_expected_target_hours: number;
  targets_with_eligible_forecast: number;
  targets_missing_eligible_forecast: number;
  targets_with_complete_actual: number;
  targets_missing_or_incomplete_actual: number;
  matched_pairs_evaluated: number;
  coverage_percentage: number;
  excluded_targets_count: number;
}

export interface AccuracySummaryResponse {
  decision_date_from: string;
  decision_date_to: string;
  delivery_date_from: string;
  delivery_date_to: string;
  cutoff_time: string;
  cutoff_timezone: string;
  sample_count: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  mean_bias_mw: number | null;
  p50_absolute_error_mw: number | null;
  p90_absolute_error_mw: number | null;
  p95_absolute_error_mw: number | null;
  wape: number | null;
  wape_percentage: number | null;
  total_forecast_energy_mwh: number | null;
  total_actual_energy_mwh: number | null;
  total_absolute_error_mwh: number | null;
  wape_unavailable_reason: string | null;
  coverage: CoverageStats;
}

export interface DiurnalMetricItem {
  hour_local: string;
  sample_count: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  mean_bias_mw: number | null;
  wape: number | null;
  mean_forecast_mw: number | null;
  mean_actual_mw: number | null;
}

export interface DiurnalResponse {
  decision_date_from: string;
  decision_date_to: string;
  cutoff_time: string;
  cutoff_timezone: string;
  diurnal_profile: DiurnalMetricItem[];
}

export interface HorizonMetricItem {
  horizon_bucket: string;
  sample_count: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  mean_bias_mw: number | null;
  wape: number | null;
  mean_forecast_mw: number | null;
  mean_actual_mw: number | null;
}

export interface DistributionResponse {
  decision_date_from: string;
  decision_date_to: string;
  cutoff_time: string;
  cutoff_timezone: string;
  horizon_groups: HorizonMetricItem[];
  error_quantiles: Record<string, number | null>;
}
