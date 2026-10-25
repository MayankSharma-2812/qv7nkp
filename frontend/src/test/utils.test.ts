import { describe, it, expect } from "vitest";
import { 
  formatMW, 
  formatSignedMW, 
  formatPercent, 
  formatMWh, 
  formatDate, 
  formatTime,
  deriveDeliveryDate 
} from "@/lib/utils";

describe("lib/utils formatting and date logic", () => {
  it("formats MW numbers with commas and decimals", () => {
    expect(formatMW(1234.56, true)).toBe("1,234.6 MW");
    expect(formatMW(0, true)).toBe("0.0 MW");
    expect(formatMW(null)).toBe("—");
    expect(formatMW(undefined)).toBe("—");
  });

  it("formats signed MW numbers with explicit plus/minus signs", () => {
    expect(formatSignedMW(543.21, true)).toBe("+543.2 MW");
    expect(formatSignedMW(-120.4, true)).toBe("-120.4 MW");
    expect(formatSignedMW(0, true)).toBe("0.0 MW");
    expect(formatSignedMW(null)).toBe("—");
  });

  it("formats percentages with default and custom decimals", () => {
    expect(formatPercent(17.84)).toBe("17.8%");
    expect(formatPercent(17.84, 2)).toBe("17.84%");
    expect(formatPercent(null)).toBe("N/A");
    expect(formatPercent(undefined)).toBe("N/A");
  });

  it("formats energy in GWh or MWh depending on scale", () => {
    expect(formatMWh(1500000)).toBe("1,500.0 GWh");
    expect(formatMWh(500)).toBe("500.0 MWh");
    expect(formatMWh(null)).toBe("—");
  });

  it("formats ISO timestamps to date and time", () => {
    const iso = "2026-01-01T14:30:00Z";
    expect(formatDate(iso)).toMatch(/2026/);
    expect(formatTime(iso)).toMatch(/14:30/);
    expect(formatDate(null)).toBe("—");
    expect(formatTime(null)).toBe("—");
  });

  it("derives next-day delivery date correctly across month boundaries", () => {
    expect(deriveDeliveryDate("2026-01-01")).toBe("2026-01-02");
    expect(deriveDeliveryDate("2026-01-31")).toBe("2026-02-01");
    expect(deriveDeliveryDate("2026-02-28")).toBe("2026-03-01");
  });
});
