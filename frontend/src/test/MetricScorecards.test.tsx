import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricScorecards } from "@/components/accuracy/MetricScorecards";
import { AccuracySummaryResponse } from "@/api/types";

describe("MetricScorecards Component", () => {
  const mockSummary: AccuracySummaryResponse = {
    decision_date_from: "2026-01-01",
    decision_date_to: "2026-01-31",
    delivery_date_from: "2026-01-02",
    delivery_date_to: "2026-02-01",
    cutoff_time: "10:00:00",
    cutoff_timezone: "Europe/London",
    sample_count: 744,
    mae_mw: 2013.01,
    rmse_mw: 2505.94,
    mean_bias_mw: 1729.93,
    p50_absolute_error_mw: 1680.5,
    p90_absolute_error_mw: 3890.2,
    p95_absolute_error_mw: 4500.0,
    wape: 0.1784,
    wape_percentage: 17.84,
    total_forecast_energy_mwh: 9680000,
    total_actual_energy_mwh: 8390000,
    total_absolute_error_mwh: 1497679.44,
    wape_unavailable_reason: null,
    coverage: {
      total_expected_target_hours: 744,
      targets_with_eligible_forecast: 744,
      targets_missing_eligible_forecast: 0,
      targets_with_complete_actual: 744,
      targets_missing_or_incomplete_actual: 0,
      matched_pairs_evaluated: 744,
      coverage_percentage: 100.0,
      excluded_targets_count: 0,
    },
  };

  it("renders statistical metrics correctly", () => {
    render(<MetricScorecards summary={mockSummary} />);

    expect(screen.getByText("MAE")).toBeInTheDocument();
    expect(screen.getByText("2,013.0")).toBeInTheDocument();

    expect(screen.getByText("RMSE")).toBeInTheDocument();
    expect(screen.getByText("2,505.9")).toBeInTheDocument();

    expect(screen.getByText("Mean Bias")).toBeInTheDocument();
    expect(screen.getByText(/\+1,729\.9/)).toBeInTheDocument();

    expect(screen.getByText("Systematic Over-forecast")).toBeInTheDocument();
    expect(screen.getByText("17.8%")).toBeInTheDocument();
    expect(screen.getByText("3,890.2")).toBeInTheDocument();
  });

  it("renders N/A and unavailable reason when WAPE is null (never displays 0.0%)", () => {
    const summaryWithNullWape: AccuracySummaryResponse = {
      ...mockSummary,
      wape: null,
      wape_unavailable_reason: "Sum of actual generation is zero",
    };

    render(<MetricScorecards summary={summaryWithNullWape} />);

    expect(screen.getByText("N/A")).toBeInTheDocument();
    expect(screen.getByText("Sum of actual generation is zero")).toBeInTheDocument();
  });
});
