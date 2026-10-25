import {
  ResponsiveContainer,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ComposedChart,
} from "recharts";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { DiurnalMetricItem } from "@/api/types";
import { formatMW } from "@/lib/utils";

interface DiurnalChartProps {
  data: DiurnalMetricItem[];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    payload: DiurnalMetricItem;
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0].payload;

  return (
    <div className="rounded-xl border border-[#E2E0D8] bg-white p-3 shadow-lg text-xs space-y-1.5 min-w-[200px]">
      <div className="font-bold text-[#141F1B] border-b border-[#E2E0D8]/60 pb-1">
        Delivery Hour: {item.hour_local} (Europe/London)
      </div>
      <div className="flex justify-between">
        <span className="text-[#5A6B64]">Sample Days (N):</span>
        <span className="font-medium text-[#141F1B]">{item.sample_count}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-[#0D6E6E] font-medium">MAE:</span>
        <span className="font-bold tabular-nums text-[#141F1B]">{formatMW(item.mae_mw)} MW</span>
      </div>
      <div className="flex justify-between">
        <span className="text-[#5A6B64]">Mean Bias (F - A):</span>
        <span
          className={`font-bold tabular-nums ${
            (item.mean_bias_mw ?? 0) > 0 ? "text-[#E06D53]" : "text-[#0D6E6E]"
          }`}
        >
          {item.mean_bias_mw !== null && item.mean_bias_mw > 0 ? "+" : ""}
          {formatMW(item.mean_bias_mw)} MW
        </span>
      </div>
      <div className="flex justify-between text-[11px] text-[#5A6B64] pt-1 border-t border-[#E2E0D8]/40">
        <span>Mean Forecast: {formatMW(item.mean_forecast_mw)} MW</span>
        <span>Mean Actual: {formatMW(item.mean_actual_mw)} MW</span>
      </div>
    </div>
  );
}

export function DiurnalChart({ data }: DiurnalChartProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle>Diurnal Error Curve</CardTitle>
            <CardDescription>
              Average forecast error and absolute error by local hour of the delivery day (00:00 to 23:00 London time)
            </CardDescription>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium">
            <span className="flex items-center gap-1.5 text-[#E06D53]">
              <span className="h-2.5 w-2.5 rounded-full bg-[#E06D53]" /> Mean Bias (MW)
            </span>
            <span className="flex items-center gap-1.5 text-[#0D6E6E]">
              <span className="h-2.5 w-2.5 rounded-full bg-[#0D6E6E]" /> MAE (MW)
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[320px] w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E0D8" vertical={false} />
              <XAxis
                dataKey="hour_local"
                stroke="#5A6B64"
                tick={{ fontSize: 10, fill: "#5A6B64" }}
                tickLine={false}
                axisLine={{ stroke: "#E2E0D8" }}
                dy={6}
              />
              <YAxis
                stroke="#5A6B64"
                tick={{ fontSize: 10, fill: "#5A6B64" }}
                tickLine={false}
                axisLine={{ stroke: "#E2E0D8" }}
                tickFormatter={(val) => `${val.toLocaleString("en-GB")}`}
                dx={-4}
                label={{ value: "MW", angle: -90, position: "insideLeft", offset: 0, fontSize: 10, fill: "#5A6B64" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="mean_bias_mw" name="Mean Bias" fill="#E06D53" radius={[4, 4, 0, 0]} opacity={0.8} />
              <Line
                type="monotone"
                dataKey="mae_mw"
                name="MAE"
                stroke="#0D6E6E"
                strokeWidth={2}
                dot={{ r: 2.5, fill: "#0D6E6E" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
