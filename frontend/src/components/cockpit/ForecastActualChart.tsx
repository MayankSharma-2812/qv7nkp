import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { ForecastDecisionItem } from "@/api/types";
import { formatMW, formatUtcToLondon } from "@/lib/utils";

interface ForecastActualChartProps {
  forecasts: ForecastDecisionItem[];
  deliveryDate: string;
  cutoff: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    payload: ForecastDecisionItem & { localTimeLabel: string };
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const item = payload[0].payload;
  const isOver = (item.error_mw ?? 0) > 0;

  return (
    <div className="rounded-xl border border-[#E2E0D8] bg-white p-3.5 shadow-lg text-xs space-y-2 min-w-[220px]">
      <div className="font-bold text-[#141F1B] border-b border-[#E2E0D8]/60 pb-1.5 flex items-center justify-between">
        <span>Delivery: {item.localTimeLabel}</span>
        <span className="text-[10px] text-[#5A6B64] font-normal">Europe/London</span>
      </div>

      <div className="space-y-1.5 pt-0.5">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-[#0D6E6E] font-medium">
            <span className="h-2 w-2 rounded-full bg-[#0D6E6E]" /> Forecast:
          </span>
          <span className="font-bold text-[#141F1B] tabular-nums">{formatMW(item.forecast_generation_mw)} MW</span>
        </div>

        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-[#E06D53] font-medium">
            <span className="h-2 w-2 rounded-full bg-[#E06D53]" /> Actual Outturn:
          </span>
          <span className="font-bold text-[#141F1B] tabular-nums">{formatMW(item.actual_generation_mw)} MW</span>
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-[#E2E0D8]/40">
          <span className="text-[#5A6B64]">Signed Error (F - A):</span>
          <span
            className={`font-bold tabular-nums ${
              isOver ? "text-[#E06D53]" : "text-[#0D6E6E]"
            }`}
          >
            {item.error_mw !== null && item.error_mw > 0 ? "+" : ""}
            {formatMW(item.error_mw)} MW
          </span>
        </div>

        <div className="flex items-center justify-between text-[11px] text-[#5A6B64]">
          <span>Absolute Error:</span>
          <span className="font-medium text-[#141F1B] tabular-nums">{formatMW(item.absolute_error_mw)} MW</span>
        </div>
      </div>

      <div className="pt-2 border-t border-[#E2E0D8]/60 text-[10px] text-[#5A6B64] space-y-0.5">
        <div>
          Published: <span className="text-[#141F1B] font-medium">{formatUtcToLondon(item.publish_time_utc)}</span> (London) /{" "}
          <span className="text-[#141F1B] font-medium">{item.publish_time_utc ? item.publish_time_utc.slice(11, 16) : "—"}</span> UTC
        </div>
        <div>
          Lead Horizon: <span className="text-[#141F1B] font-medium">{item.horizon_hours !== null ? `${item.horizon_hours.toFixed(1)} hrs` : "—"}</span>
        </div>
      </div>
    </div>
  );
}

export function ForecastActualChart({ forecasts, deliveryDate, cutoff }: ForecastActualChartProps) {
  const chartData = forecasts.map((f) => ({
    ...f,
    localTimeLabel: `${String(f.delivery_hour_local).padStart(2, "0")}:00`,
  }));

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle>Day-Ahead Wind Forecast vs. Actual Outturn</CardTitle>
            <CardDescription>
              Comparing operational forecast available as of {cutoff.slice(0, 5)} Europe/London against 1-hour metred generation on {deliveryDate}
            </CardDescription>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium">
            <span className="flex items-center gap-1.5 text-[#0D6E6E]">
              <span className="h-2.5 w-2.5 rounded-full bg-[#0D6E6E]" /> Forecast (WINDFOR)
            </span>
            <span className="flex items-center gap-1.5 text-[#E06D53]">
              <span className="h-2.5 w-2.5 rounded-full bg-[#E06D53]" /> Actual Outturn (FUELHH)
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] w-full pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E0D8" vertical={false} />
              <XAxis
                dataKey="localTimeLabel"
                stroke="#5A6B64"
                tick={{ fontSize: 11, fill: "#5A6B64" }}
                tickLine={false}
                axisLine={{ stroke: "#E2E0D8" }}
                dy={8}
                label={{ value: "Delivery Hour (Europe/London)", position: "insideBottom", offset: -16, fontSize: 11, fill: "#5A6B64" }}
              />
              <YAxis
                stroke="#5A6B64"
                tick={{ fontSize: 11, fill: "#5A6B64" }}
                tickLine={false}
                axisLine={{ stroke: "#E2E0D8" }}
                tickFormatter={(val) => `${val.toLocaleString("en-GB")}`}
                dx={-4}
                label={{ value: "Power (MW)", angle: -90, position: "insideLeft", offset: -2, fontSize: 11, fill: "#5A6B64" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} content={() => null} />
              <Line
                type="monotone"
                dataKey="forecast_generation_mw"
                name="Forecast"
                stroke="#0D6E6E"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#0D6E6E", strokeWidth: 0 }}
                activeDot={{ r: 5, stroke: "#FFFFFF", strokeWidth: 2 }}
              />
              <Line
                type="monotone"
                dataKey="actual_generation_mw"
                name="Actual Outturn"
                stroke="#E06D53"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#E06D53", strokeWidth: 0 }}
                activeDot={{ r: 5, stroke: "#FFFFFF", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
