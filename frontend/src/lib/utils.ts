import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMW(val: number | null | undefined, withUnit = false): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  const formatted = new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  }).format(val);
  return withUnit ? `${formatted} MW` : formatted;
}

export function formatSignedMW(val: number | null | undefined, withUnit = false): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  const sign = val > 0 ? "+" : "";
  const formatted = new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  }).format(val);
  const result = `${sign}${formatted}`;
  return withUnit ? `${result} MW` : result;
}

export function formatGWh(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(val / 1000.0);
}

export function formatMWh(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  if (Math.abs(val) >= 10000) {
    return `${(val / 1000).toLocaleString("en-GB", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} GWh`;
  }
  return `${val.toLocaleString("en-GB", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} MWh`;
}

export function formatPercent(val: number | null | undefined, digits = 1): string {
  if (val === null || val === undefined || isNaN(val)) return "N/A";
  return `${val.toFixed(digits)}%`;
}

export function formatPercentage(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return `${(val * 100).toFixed(1)}%`;
}

export function formatUtcToLondon(isoUtc: string | null | undefined): string {
  if (!isoUtc) return "—";
  try {
    const d = new Date(isoUtc);
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/London",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(d);
  } catch {
    return isoUtc;
  }
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/London",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(d);
  } catch {
    return iso;
  }
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/London",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(d);
  } catch {
    return iso;
  }
}

export function deriveDeliveryDate(decisionDate: string): string {
  const parts = decisionDate.split("-").map(Number);
  if (parts.length !== 3) return decisionDate;
  const d = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}
