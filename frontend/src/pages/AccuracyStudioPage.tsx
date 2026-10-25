import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { AccuracyControls } from "@/components/accuracy/AccuracyControls";
import { MetricScorecards } from "@/components/accuracy/MetricScorecards";
import { DiurnalChart } from "@/components/accuracy/DiurnalChart";
import { HorizonChart } from "@/components/accuracy/HorizonChart";
import { CoveragePanel } from "@/components/accuracy/CoveragePanel";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function AccuracyStudioPage() {
  const [dateFrom, setDateFrom] = useState<string>("2026-01-01");
  const [dateTo, setDateTo] = useState<string>("2026-01-31");
  const [cutoff, setCutoff] = useState<string>("10:00:00");

  const summaryQuery = useQuery({
    queryKey: ["accuracySummary", dateFrom, dateTo, cutoff],
    queryFn: ({ signal }) => api.getAccuracySummary(dateFrom, dateTo, cutoff, signal),
    staleTime: 5 * 60 * 1000,
  });

  const diurnalQuery = useQuery({
    queryKey: ["accuracyDiurnal", dateFrom, dateTo, cutoff],
    queryFn: ({ signal }) => api.getAccuracyDiurnal(dateFrom, dateTo, cutoff, signal),
    staleTime: 5 * 60 * 1000,
  });

  const distQuery = useQuery({
    queryKey: ["accuracyDistribution", dateFrom, dateTo, cutoff],
    queryFn: ({ signal }) => api.getAccuracyDistribution(dateFrom, dateTo, cutoff, signal),
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = summaryQuery.isLoading || diurnalQuery.isLoading || distQuery.isLoading;
  const isError = summaryQuery.isError || diurnalQuery.isError || distQuery.isError;

  return (
    <div className="space-y-6">
      <AccuracyControls
        dateFrom={dateFrom}
        dateTo={dateTo}
        cutoff={cutoff}
        onDateFromChange={setDateFrom}
        onDateToChange={setDateTo}
        onCutoffChange={setCutoff}
      />

      {isLoading && (
        <div className="space-y-6" aria-label="Loading accuracy analytics">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-28 w-full rounded-xl" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Skeleton className="h-[340px] w-full rounded-xl" />
            <Skeleton className="h-[340px] w-full rounded-xl" />
          </div>
          <Skeleton className="h-40 w-full rounded-xl" />
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-800">
          <AlertTriangle className="mx-auto h-8 w-8 text-red-600 mb-2" />
          <h3 className="text-sm font-bold">Failed to load accuracy evaluation data</h3>
          <p className="mt-1 text-xs text-red-700">
            One or more analytics queries failed. Please check your date range parameters or network connectivity.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              summaryQuery.refetch();
              diurnalQuery.refetch();
              distQuery.refetch();
            }}
            className="mt-4 gap-2 bg-white text-xs border-red-300 hover:bg-red-100"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Retry Queries
          </Button>
        </div>
      )}

      {!isLoading && !isError && summaryQuery.data && (
        <div className="space-y-6">
          {/* Top 5 KPI Scorecards */}
          <MetricScorecards summary={summaryQuery.data.data} />

          {/* Diurnal Error Profile & Horizon Degradation */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {diurnalQuery.data && (
              <DiurnalChart data={diurnalQuery.data.data.diurnal_profile} />
            )}
            {distQuery.data && (
              <HorizonChart data={distQuery.data.data.horizon_groups} />
            )}
          </div>

          {/* Verification Audit & Coverage Quality Panel */}
          <CoveragePanel coverage={summaryQuery.data.data.coverage} />
        </div>
      )}
    </div>
  );
}
