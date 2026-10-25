import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { DecisionControls } from "@/components/cockpit/DecisionControls";
import { DecisionKpis } from "@/components/cockpit/DecisionKpis";
import { ForecastActualChart } from "@/components/cockpit/ForecastActualChart";
import { DecisionHourlyTable } from "@/components/cockpit/DecisionHourlyTable";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function DecisionCockpitPage() {
  const [decisionDate, setDecisionDate] = useState<string>("2026-01-01");
  const [cutoff, setCutoff] = useState<string>("10:00:00");

  const {
    data: timedRes,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["decisionForecast", decisionDate, cutoff],
    queryFn: ({ signal }) => api.getDecisionForecast(decisionDate, cutoff, signal),
    staleTime: 5 * 60 * 1000,
  });

  const response = timedRes?.data;

  return (
    <div className="space-y-6">
      {/* Top Controls */}
      <DecisionControls
        decisionDate={decisionDate}
        cutoff={cutoff}
        deliveryDate={response?.delivery_date}
        onDecisionDateChange={setDecisionDate}
        onCutoffChange={setCutoff}
      />

      {/* Loading Skeleton State */}
      {isLoading && (
        <div className="space-y-6" aria-label="Loading decision cockpit">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-[420px] w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-800">
          <AlertTriangle className="mx-auto h-8 w-8 text-red-600 mb-2" />
          <h3 className="text-sm font-bold">Failed to load forecast decision data</h3>
          <p className="mt-1 text-xs text-red-700">
            {error instanceof Error ? error.message : "An unexpected network error occurred."}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="mt-4 gap-2 bg-white text-xs border-red-300 hover:bg-red-100"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Retry Request
          </Button>
        </div>
      )}

      {/* Populated Data View */}
      {!isLoading && !isError && response && (
        <div className="space-y-6">
          {/* Subtle refreshing indicator if background fetching */}
          {isFetching && (
            <div className="flex items-center justify-end text-[11px] text-[#5A6B64] gap-1">
              <RefreshCw className="h-3 w-3 animate-spin text-[#174D3E]" /> Updating in background...
            </div>
          )}

          {/* Key Metrics */}
          <DecisionKpis forecasts={response.forecasts} />

          {/* Main Visual Comparison Chart */}
          <ForecastActualChart
            forecasts={response.forecasts}
            deliveryDate={response.delivery_date}
            cutoff={response.cutoff_time}
          />

          {/* Granular Breakdown Table with CSV Export */}
          <DecisionHourlyTable
            forecasts={response.forecasts}
            deliveryDate={response.delivery_date}
            decisionDate={response.decision_date}
            cutoff={response.cutoff_time}
          />
        </div>
      )}
    </div>
  );
}
