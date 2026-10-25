import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { HorizonMetricItem } from "@/api/types";
import { formatMW } from "@/lib/utils";

interface HorizonChartProps {
  data: HorizonMetricItem[];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    payload: HorizonMetricItem;
  }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0].payload;

  return (
    <div className="rounded-xl border border-[#E2E0D8] bg-white p-3 shadow-lg text-xs space-y-1.5 min-w-[190px]">
      <div className="font-bold text-[#141F1B] border-b border-[#E2E0D8]/60 pb-1">
        Lead Horizon: {item.horizon_bucket}
      </div>
      <div className="flex justify-between">
        <span className="text-[#5A6B64]">Observations (N):</span>
        <span className="font-medium text-[#141F1B]">{item.sample_count}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-[#0D6E6E] font-medium">MAE:</span>
        <span className="font-bold tabular-nums text-[#141F1B]">{formatMW(item.mae_mw)} MW</span>
      </div>
      <div className="flex justify-between">
        <span className="text-[#5A6B64]">Mean Bias:</span>
        <span
          className={`font-bold tabular-nums ${
            (item.mean_bias_mw ?? 0) > 0 ? "text-[#E06D53]" : "text-[#0D6E6E]"
          }`}
        >
          {item.mean_bias_mw !== null && item.mean_bias_mw > 0 ? "+" : ""}
          {formatMW(item.mean_bias_mw)} MW
        </span>
      </div>
    </div>
  );
}

export function HorizonChart({ data }: HorizonChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Forecast Horizon Degradation</CardTitle>
        <CardDescription>
          MAE by lead horizon (hours elapsed between forecast publication and target delivery)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E0D8" vertical={false} />
              <XAxis
                dataKey="horizon_bucket"
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
                label={{ value: "MAE (MW)", angle: -90, position: "insideLeft", offset: 0, fontSize: 10, fill: "#5A6B64" }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="mae_mw" name="MAE" fill="#174D3E" radius={[4, 4, 0, 0]} opacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
