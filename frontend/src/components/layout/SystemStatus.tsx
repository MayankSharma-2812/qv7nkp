import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Activity, Database, CheckCircle2, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface SystemStatusProps {
  lastLatencyMs?: number;
}

export function SystemStatus({ lastLatencyMs }: SystemStatusProps) {
  const { data: healthTimed, isError: healthError } = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.getHealth(signal),
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  });

  const { data: readyTimed, isError: readyError } = useQuery({
    queryKey: ["ready"],
    queryFn: ({ signal }) => api.getReady(signal),
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  });

  const isHealthy = !healthError && healthTimed?.data?.status === "ok";
  const isReady = !readyError && readyTimed?.data?.status === "ready";
  const latency = lastLatencyMs ?? readyTimed?.latencyMs ?? healthTimed?.latencyMs ?? 0;

  return (
    <div className="rounded-xl border border-[#E2E0D8] bg-white p-3 shadow-xs">
      <div className="flex items-center justify-between pb-2 border-b border-[#E2E0D8]/60">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[#5A6B64]">System Health</span>
        {isHealthy && isReady ? (
          <Badge variant="accent" className="h-5 px-1.5 text-[10px] gap-1">
            <CheckCircle2 className="h-3 w-3 text-[#174D3E]" /> Ready
          </Badge>
        ) : (
          <Badge variant="warning" className="h-5 px-1.5 text-[10px] gap-1">
            <AlertTriangle className="h-3 w-3 text-amber-700" /> Offline
          </Badge>
        )}
      </div>

      <div className="mt-2.5 space-y-2 text-xs">
        <div className="flex items-center justify-between text-[#5A6B64]">
          <span className="flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5 text-[#174D3E]" /> API Latency
          </span>
          <span className="font-medium text-[#141F1B] tabular-nums">{latency > 0 ? `${latency} ms` : "—"}</span>
        </div>

        <div className="flex items-center justify-between text-[#5A6B64]">
          <span className="flex items-center gap-1.5">
            <Database className="h-3.5 w-3.5 text-[#174D3E]" /> Actuals Stored
          </span>
          <span className="font-medium text-[#141F1B] tabular-nums">
            {readyTimed?.data?.actual_observations_count?.toLocaleString("en-GB") ?? "—"}
          </span>
        </div>

        <div className="flex items-center justify-between text-[#5A6B64]">
          <span className="flex items-center gap-1.5">
            <Database className="h-3.5 w-3.5 text-[#174D3E]" /> Forecasts Stored
          </span>
          <span className="font-medium text-[#141F1B] tabular-nums">
            {readyTimed?.data?.forecast_observations_count?.toLocaleString("en-GB") ?? "—"}
          </span>
        </div>
      </div>
      <div className="mt-2 pt-2 border-t border-[#E2E0D8]/40 text-[10px] text-[#5A6B64] text-center">
        Historical SQLite • January 2026
      </div>
    </div>
  );
}
