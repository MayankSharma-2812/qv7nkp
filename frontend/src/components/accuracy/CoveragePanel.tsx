import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { CoverageStats } from "@/api/types";
import { CheckCircle2, ShieldCheck, Database, Calendar } from "lucide-react";

interface CoveragePanelProps {
  coverage: CoverageStats;
}

export function CoveragePanel({ coverage }: CoveragePanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Dataset Coverage & Verification Audit</CardTitle>
        <CardDescription>
          Data completeness checks across the evaluated January 2026 decision window
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#5A6B64] uppercase tracking-wider mb-1">
              <Calendar className="h-3.5 w-3.5 text-[#174D3E]" /> Expected Hours
            </div>
            <div className="text-xl font-bold text-[#141F1B] tabular-nums">
              {coverage.total_expected_target_hours} <span className="text-xs font-normal text-[#5A6B64]">intervals</span>
            </div>
            <p className="text-[11px] text-[#5A6B64] mt-1">Full delivery calendar</p>
          </div>

          <div className="rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#5A6B64] uppercase tracking-wider mb-1">
              <Database className="h-3.5 w-3.5 text-[#174D3E]" /> Eligible Forecasts
            </div>
            <div className="text-xl font-bold text-[#141F1B] tabular-nums">
              {coverage.targets_with_eligible_forecast} <span className="text-xs font-normal text-[#5A6B64]">hours</span>
            </div>
            <p className="text-[11px] text-[#5A6B64] mt-1">Available at decision cutoff</p>
          </div>

          <div className="rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#5A6B64] uppercase tracking-wider mb-1">
              <ShieldCheck className="h-3.5 w-3.5 text-[#174D3E]" /> Complete Actuals
            </div>
            <div className="text-xl font-bold text-[#141F1B] tabular-nums">
              {coverage.targets_with_complete_actual} <span className="text-xs font-normal text-[#5A6B64]">hours</span>
            </div>
            <p className="text-[11px] text-[#5A6B64] mt-1">Both SPs metred & valid</p>
          </div>

          <div className="rounded-lg border border-[#E2E0D8] bg-[#F7F6F1] p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#5A6B64] uppercase tracking-wider mb-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-[#174D3E]" /> Evaluated Match
            </div>
            <div className="text-xl font-bold text-[#141F1B] tabular-nums text-[#174D3E]">
              {coverage.coverage_percentage.toFixed(1)}%
            </div>
            <p className="text-[11px] text-[#5A6B64] mt-1">
              {coverage.matched_pairs_evaluated} pairs (0 excluded)
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
