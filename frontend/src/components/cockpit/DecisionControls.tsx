import { Calendar, Clock, AlertCircle } from "lucide-react";

interface DecisionControlsProps {
  decisionDate: string;
  cutoff: string;
  deliveryDate?: string;
  onDecisionDateChange: (date: string) => void;
  onCutoffChange: (cutoff: string) => void;
}

export function DecisionControls({
  decisionDate,
  cutoff,
  deliveryDate,
  onDecisionDateChange,
  onCutoffChange,
}: DecisionControlsProps) {
  // Generate date options for January 2026
  const dateOptions = Array.from({ length: 31 }, (_, i) => {
    const day = String(i + 1).padStart(2, "0");
    return `2026-01-${day}`;
  });

  const cutoffOptions = [
    { value: "09:00:00", label: "09:00 Europe/London (Early Cutoff)" },
    { value: "10:00:00", label: "10:00 Europe/London (Default Benchmark)" },
    { value: "11:00:00", label: "11:00 Europe/London (Mid-Day Cutoff)" },
    { value: "12:00:00", label: "12:00 Europe/London (EPEX Spot Closure)" },
  ];

  return (
    <div className="rounded-xl border border-[#E2E0D8] bg-white p-4 shadow-xs">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Decision Date selector */}
          <div className="flex flex-col gap-1">
            <label htmlFor="decision-date-select" className="text-xs font-semibold uppercase tracking-wider text-[#5A6B64] flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-[#174D3E]" /> Decision Date (D-1)
            </label>
            <select
              id="decision-date-select"
              value={decisionDate}
              onChange={(e) => onDecisionDateChange(e.target.value)}
              className="h-9 rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] px-3 py-1.5 text-xs font-medium text-[#141F1B] focus:border-[#174D3E] focus:outline-none focus:ring-1 focus:ring-[#174D3E]"
            >
              {dateOptions.map((d) => (
                <option key={d} value={d}>
                  {d} (Decision)
                </option>
              ))}
            </select>
          </div>

          {/* Cutoff time selector */}
          <div className="flex flex-col gap-1">
            <label htmlFor="cutoff-time-select" className="text-xs font-semibold uppercase tracking-wider text-[#5A6B64] flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-[#174D3E]" /> Decision Cutoff
            </label>
            <select
              id="cutoff-time-select"
              value={cutoff}
              onChange={(e) => onCutoffChange(e.target.value)}
              className="h-9 rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] px-3 py-1.5 text-xs font-medium text-[#141F1B] focus:border-[#174D3E] focus:outline-none focus:ring-1 focus:ring-[#174D3E]"
            >
              {cutoffOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Resolved Delivery Date Callout */}
        <div className="flex items-center gap-3 rounded-lg bg-[#DCE8DF]/50 px-3.5 py-2 border border-[#DCE8DF]">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-wider text-[#174D3E]">Target Delivery Date (D)</div>
            <div className="text-sm font-bold text-[#141F1B]">
              {deliveryDate || "Calculating..."}
            </div>
          </div>
        </div>
      </div>

      {/* Explanatory Methodology Footnote */}
      <div className="mt-3 flex items-start gap-1.5 text-[11px] text-[#5A6B64] border-t border-[#E2E0D8]/50 pt-2.5">
        <AlertCircle className="h-3.5 w-3.5 text-amber-700 shrink-0 mt-0.5" />
        <span>
          <strong>Temporal Rule:</strong> Only forecasts published on or before {cutoff.slice(0, 5)} Europe/London on the decision date ({decisionDate}) are considered. Future revisions published post-cutoff or intraday are strictly excluded.
        </span>
      </div>
    </div>
  );
}
