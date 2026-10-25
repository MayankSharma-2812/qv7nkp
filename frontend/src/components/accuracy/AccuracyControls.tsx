import { Calendar, Clock, Info } from "lucide-react";

interface AccuracyControlsProps {
  dateFrom: string;
  dateTo: string;
  cutoff: string;
  onDateFromChange: (val: string) => void;
  onDateToChange: (val: string) => void;
  onCutoffChange: (val: string) => void;
}

export function AccuracyControls({
  dateFrom,
  dateTo,
  cutoff,
  onDateFromChange,
  onDateToChange,
  onCutoffChange,
}: AccuracyControlsProps) {
  const dateOptions = Array.from({ length: 31 }, (_, i) => {
    const day = String(i + 1).padStart(2, "0");
    return `2026-01-${day}`;
  });

  const cutoffOptions = [
    { value: "09:00:00", label: "09:00 Europe/London" },
    { value: "10:00:00", label: "10:00 Europe/London (Default Benchmark)" },
    { value: "11:00:00", label: "11:00 Europe/London" },
    { value: "12:00:00", label: "12:00 Europe/London" },
  ];

  return (
    <div className="rounded-xl border border-[#E2E0D8] bg-white p-4 shadow-xs">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          {/* Decision Date From */}
          <div className="flex flex-col gap-1">
            <label htmlFor="date-from-select" className="text-xs font-semibold uppercase tracking-wider text-[#5A6B64] flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-[#174D3E]" /> Decision From
            </label>
            <select
              id="date-from-select"
              value={dateFrom}
              onChange={(e) => onDateFromChange(e.target.value)}
              className="h-9 rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] px-3 py-1.5 text-xs font-medium text-[#141F1B] focus:border-[#174D3E] focus:outline-none focus:ring-1 focus:ring-[#174D3E]"
            >
              {dateOptions.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Decision Date To */}
          <div className="flex flex-col gap-1">
            <label htmlFor="date-to-select" className="text-xs font-semibold uppercase tracking-wider text-[#5A6B64] flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-[#174D3E]" /> Decision To
            </label>
            <select
              id="date-to-select"
              value={dateTo}
              onChange={(e) => onDateToChange(e.target.value)}
              className="h-9 rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] px-3 py-1.5 text-xs font-medium text-[#141F1B] focus:border-[#174D3E] focus:outline-none focus:ring-1 focus:ring-[#174D3E]"
            >
              {dateOptions.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Cutoff Selector */}
          <div className="flex flex-col gap-1">
            <label htmlFor="accuracy-cutoff-select" className="text-xs font-semibold uppercase tracking-wider text-[#5A6B64] flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-[#174D3E]" /> Gate Closure Cutoff
            </label>
            <select
              id="accuracy-cutoff-select"
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

        <div className="flex items-center gap-2 rounded-lg bg-[#DCE8DF]/40 px-3 py-2 border border-[#DCE8DF] text-xs text-[#174D3E]">
          <Info className="h-4 w-4 shrink-0" />
          <span>Dates govern day-ahead purchasing decisions (delivery occurs on D+1).</span>
        </div>
      </div>
    </div>
  );
}
