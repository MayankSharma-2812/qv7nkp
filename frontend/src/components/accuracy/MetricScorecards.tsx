import { Card, CardContent } from "@/components/ui/card";
import { formatMW } from "@/lib/utils";
import { AccuracySummaryResponse } from "@/api/types";
import { HelpCircle } from "lucide-react";

interface MetricScorecardsProps {
  summary: AccuracySummaryResponse;
}

export function MetricScorecards({ summary }: MetricScorecardsProps) {
  const isOverBias = (summary.mean_bias_mw ?? 0) > 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* 1. MAE */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">MAE</span>
            <div className="group relative cursor-help">
              <HelpCircle className="h-3.5 w-3.5 text-[#5A6B64]" />
              <div className="absolute right-0 bottom-full mb-1.5 hidden w-48 rounded-lg bg-[#141F1B] p-2 text-[10px] text-white shadow-lg group-hover:block z-30">
                Mean Absolute Error: Average magnitude of volume miss without regard to sign.
              </div>
            </div>
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {formatMW(summary.mae_mw)} <span className="text-xs font-normal text-[#5A6B64]">MW</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">Average volume uncertainty</p>
        </CardContent>
      </Card>

      {/* 2. RMSE */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">RMSE</span>
            <div className="group relative cursor-help">
              <HelpCircle className="h-3.5 w-3.5 text-[#5A6B64]" />
              <div className="absolute right-0 bottom-full mb-1.5 hidden w-48 rounded-lg bg-[#141F1B] p-2 text-[10px] text-white shadow-lg group-hover:block z-30">
                Root Mean Square Error: Penalizes large misses heavily, reflecting peak imbalance exposure risk.
              </div>
            </div>
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {formatMW(summary.rmse_mw)} <span className="text-xs font-normal text-[#5A6B64]">MW</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">Heavy-penalty tail metric</p>
        </CardContent>
      </Card>

      {/* 3. Mean Signed Bias */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Mean Bias</span>
            <div className="group relative cursor-help">
              <HelpCircle className="h-3.5 w-3.5 text-[#5A6B64]" />
              <div className="absolute right-0 bottom-full mb-1.5 hidden w-48 rounded-lg bg-[#141F1B] p-2 text-[10px] text-white shadow-lg group-hover:block z-30">
                Signed Error (F - A). Positive = Over-forecast (shortfall risk); Negative = Under-forecast (spill risk).
              </div>
            </div>
          </div>
          <div
            className={`text-2xl font-bold tabular-nums ${
              isOverBias ? "text-[#E06D53]" : "text-[#0D6E6E]"
            }`}
          >
            {summary.mean_bias_mw !== null && summary.mean_bias_mw > 0 ? "+" : ""}
            {formatMW(summary.mean_bias_mw)}{" "}
            <span className="text-xs font-normal text-[#5A6B64]">MW</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">
            {isOverBias ? "Systematic Over-forecast" : "Systematic Under-forecast"}
          </p>
        </CardContent>
      </Card>

      {/* 4. P90 Absolute Error */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">P90 Abs Error</span>
            <div className="group relative cursor-help">
              <HelpCircle className="h-3.5 w-3.5 text-[#5A6B64]" />
              <div className="absolute right-0 bottom-full mb-1.5 hidden w-48 rounded-lg bg-[#141F1B] p-2 text-[10px] text-white shadow-lg group-hover:block z-30">
                90th Percentile: 90% of hourly errors were smaller than this value.
              </div>
            </div>
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {formatMW(summary.p90_absolute_error_mw)}{" "}
            <span className="text-xs font-normal text-[#5A6B64]">MW</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">
            P50: {formatMW(summary.p50_absolute_error_mw)} MW
          </p>
        </CardContent>
      </Card>

      {/* 5. WAPE */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">WAPE</span>
            <div className="group relative cursor-help">
              <HelpCircle className="h-3.5 w-3.5 text-[#5A6B64]" />
              <div className="absolute right-0 bottom-full mb-1.5 hidden w-52 rounded-lg bg-[#141F1B] p-2 text-[10px] text-white shadow-lg group-hover:block z-30">
                Weighted Absolute Percentage Error: sum(|Error|) / sum(Actuals). Preferred over MAPE to avoid zero-division.
              </div>
            </div>
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {summary.wape !== null
              ? `${(summary.wape * 100).toFixed(1)}%`
              : "N/A"}
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">
            {summary.wape !== null ? "Normalized volume error" : summary.wape_unavailable_reason || "Undefined"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
