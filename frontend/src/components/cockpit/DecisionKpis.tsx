import { Card, CardContent } from "@/components/ui/card";
import { formatGWh, formatMW } from "@/lib/utils";
import { Wind, Zap, Gauge, CheckCircle } from "lucide-react";
import { ForecastDecisionItem } from "@/api/types";

interface DecisionKpisProps {
  forecasts: ForecastDecisionItem[];
  isLoading?: boolean;
}

export function DecisionKpis({ forecasts }: DecisionKpisProps) {
  const matched = forecasts.filter(
    (f) => f.forecast_generation_mw !== null && f.actual_generation_mw !== null
  );

  const totalForecastMWh = forecasts.reduce(
    (acc, f) => acc + (f.forecast_generation_mw ?? 0),
    0
  );
  const totalActualMWh = forecasts.reduce(
    (acc, f) => acc + (f.actual_generation_mw ?? 0),
    0
  );

  const sumAbsError = matched.reduce(
    (acc, f) => acc + (f.absolute_error_mw ?? 0),
    0
  );
  const dailyMae = matched.length > 0 ? sumAbsError / matched.length : null;

  const sumSignedError = matched.reduce(
    (acc, f) => acc + (f.error_mw ?? 0),
    0
  );
  const dailyBias = matched.length > 0 ? sumSignedError / matched.length : null;

  const coveragePct = forecasts.length > 0
    ? Math.round((matched.length / forecasts.length) * 100)
    : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Expected Wind Generation */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Forecast Wind</span>
            <Wind className="h-4 w-4 text-[#0D6E6E]" />
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {formatGWh(totalForecastMWh)} <span className="text-xs font-normal text-[#5A6B64]">GWh</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">Day-ahead procurement expected</p>
        </CardContent>
      </Card>

      {/* 2. Delivered Actual Generation */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Actual Wind Outturn</span>
            <Zap className="h-4 w-4 text-[#E06D53]" />
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {formatGWh(totalActualMWh)} <span className="text-xs font-normal text-[#5A6B64]">GWh</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">Metred national wind outturn</p>
        </CardContent>
      </Card>

      {/* 3. Daily Mean Absolute Error & Bias */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Daily Error (MAE)</span>
            <Gauge className="h-4 w-4 text-[#174D3E]" />
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {formatMW(dailyMae)} <span className="text-xs font-normal text-[#5A6B64]">MW</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">
            Bias:{" "}
            <span
              className={`font-semibold ${
                (dailyBias ?? 0) > 0 ? "text-[#E06D53]" : "text-[#0D6E6E]"
              }`}
            >
              {dailyBias !== null && dailyBias > 0 ? "+" : ""}
              {formatMW(dailyBias)} MW
            </span>{" "}
            ({(dailyBias ?? 0) > 0 ? "Over-forecast" : "Under-forecast"})
          </p>
        </CardContent>
      </Card>

      {/* 4. Matched Interval Coverage */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between text-[#5A6B64] mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Matched Coverage</span>
            <CheckCircle className="h-4 w-4 text-[#174D3E]" />
          </div>
          <div className="text-2xl font-bold text-[#141F1B] tabular-nums">
            {matched.length} / {forecasts.length}{" "}
            <span className="text-xs font-normal text-[#5A6B64]">({coveragePct}%)</span>
          </div>
          <p className="mt-1 text-[11px] text-[#5A6B64]">Hourly intervals paired 1:1</p>
        </CardContent>
      </Card>
    </div>
  );
}
