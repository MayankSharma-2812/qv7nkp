import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DecisionHourlyTable } from "@/components/cockpit/DecisionHourlyTable";
import { ForecastDecisionItem } from "@/api/types";

describe("DecisionHourlyTable Component", () => {
  const mockForecasts: ForecastDecisionItem[] = [
    {
      target_start_utc: "2026-01-02T00:00:00Z",
      delivery_hour_local: 0,
      forecast_generation_mw: 5200.0,
      actual_generation_mw: 4800.0,
      error_mw: 400.0,
      absolute_error_mw: 400.0,
      publish_time_utc: "2026-01-01T09:45:00Z",
      horizon_hours: 14.0,
      is_actual_complete: true,
      status: "MATCHED",
    },
    {
      target_start_utc: "2026-01-02T01:00:00Z",
      delivery_hour_local: 1,
      forecast_generation_mw: 6000.0,
      actual_generation_mw: 6500.0,
      error_mw: -500.0,
      absolute_error_mw: 500.0,
      publish_time_utc: "2026-01-01T09:45:00Z",
      horizon_hours: 15.0,
      is_actual_complete: true,
      status: "MATCHED",
    },
  ];

  it("renders table with correct columns and hourly data", () => {
    render(
      <DecisionHourlyTable
        forecasts={mockForecasts}
        deliveryDate="2026-01-02"
        decisionDate="2026-01-01"
        cutoff="10:00:00"
      />
    );

    expect(screen.getByText("Hourly Delivery Interval Breakdown")).toBeInTheDocument();
    expect(screen.getByText("00:00 - 01:00")).toBeInTheDocument();
    expect(screen.getByText("01:00 - 02:00")).toBeInTheDocument();
    expect(screen.getByText("5,200.0")).toBeInTheDocument();
    expect(screen.getByText("4,800.0")).toBeInTheDocument();
    expect(screen.getByText("+400.0")).toBeInTheDocument();
    expect(screen.getByText("-500.0")).toBeInTheDocument();
  });

  it("triggers CSV export without crashing", () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    
    render(
      <DecisionHourlyTable
        forecasts={mockForecasts}
        deliveryDate="2026-01-02"
        decisionDate="2026-01-01"
        cutoff="10:00:00"
      />
    );

    const exportBtn = screen.getByRole("button", { name: /export hourly csv/i });
    fireEvent.click(exportBtn);

    expect(clickSpy).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});
