import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DecisionControls } from "@/components/cockpit/DecisionControls";

describe("DecisionControls Component", () => {
  it("renders decision date and cutoff dropdowns with correct values", () => {
    const handleDateChange = vi.fn();
    const handleCutoffChange = vi.fn();

    render(
      <DecisionControls
        decisionDate="2026-01-15"
        cutoff="10:00:00"
        deliveryDate="2026-01-16"
        onDecisionDateChange={handleDateChange}
        onCutoffChange={handleCutoffChange}
      />
    );

    const dateSelect = screen.getByLabelText(/decision date/i) as HTMLSelectElement;
    expect(dateSelect.value).toBe("2026-01-15");

    const cutoffSelect = screen.getByLabelText(/decision cutoff/i) as HTMLSelectElement;
    expect(cutoffSelect.value).toBe("10:00:00");

    expect(screen.getByText("2026-01-16")).toBeInTheDocument();
  });

  it("triggers callback on changing decision date", () => {
    const handleDateChange = vi.fn();
    const handleCutoffChange = vi.fn();

    render(
      <DecisionControls
        decisionDate="2026-01-01"
        cutoff="10:00:00"
        deliveryDate="2026-01-02"
        onDecisionDateChange={handleDateChange}
        onCutoffChange={handleCutoffChange}
      />
    );

    const dateSelect = screen.getByLabelText(/decision date/i);
    fireEvent.change(dateSelect, { target: { value: "2026-01-20" } });

    expect(handleDateChange).toHaveBeenCalledWith("2026-01-20");
  });

  it("triggers callback on changing cutoff time", () => {
    const handleDateChange = vi.fn();
    const handleCutoffChange = vi.fn();

    render(
      <DecisionControls
        decisionDate="2026-01-01"
        cutoff="10:00:00"
        deliveryDate="2026-01-02"
        onDecisionDateChange={handleDateChange}
        onCutoffChange={handleCutoffChange}
      />
    );

    const cutoffSelect = screen.getByLabelText(/decision cutoff/i);
    fireEvent.change(cutoffSelect, { target: { value: "11:00:00" } });

    expect(handleCutoffChange).toHaveBeenCalledWith("11:00:00");
  });
});
