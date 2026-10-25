import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  ShieldCheck, 
  Clock, 
  Layers, 
  Calculator, 
  AlertCircle,
  Database,
  Calendar
} from "lucide-react";

export function MethodologyPage() {
  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Intro Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="outline" className="text-xs font-semibold text-[#174D3E] border-[#174D3E]/30 bg-[#174D3E]/5">
            Documentation & Auditing
          </Badge>
          <span className="text-xs text-[#5A6B64]">WindScope Core Principles</span>
        </div>
        <h1 className="text-2xl font-bold text-[#1F2925] tracking-tight">
          Wind Forecasting & Evaluation Methodology
        </h1>
        <p className="mt-1 text-sm text-[#5A6B64] leading-relaxed">
          Comprehensive guide to temporal anti-leakage rules, time-series alignment between Elexon BMRS datasets, 
          metric definitions, and commercial implications for UK wholesale power procurement.
        </p>
      </div>

      {/* Grid of Key Concepts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Anti-Leakage & Cutoffs */}
        <Card className="border-[#C4D1C9] bg-white shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-emerald-50 text-[#174D3E]">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-base text-[#1F2925]">Temporal Anti-Leakage Policy</CardTitle>
                <CardDescription className="text-xs text-[#5A6B64]">Lookahead bias prevention</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-[#5A6B64] leading-relaxed">
            <p>
              In wholesale electricity trading, physical power for delivery day <code className="px-1 py-0.5 rounded bg-gray-100 font-mono text-[11px] text-[#1F2925]">D</code> is auctioned or contracted on day-ahead <code className="px-1 py-0.5 rounded bg-gray-100 font-mono text-[11px] text-[#1F2925]">D-1</code> prior to a decision gate (typically 10:00 or 11:00 UK time).
            </p>
            <div className="rounded-md border border-[#C4D1C9] bg-[#F2F5F3] p-3 text-[11px] font-mono text-[#1F2925] space-y-1">
              <div className="font-semibold text-[#174D3E]">Strict Cutoff Invariant:</div>
              <div>publish_time_utc ≤ cutoff_utc</div>
              <div className="text-[10px] text-[#5A6B64]">Discard any forecast revision published after the decision cutoff.</div>
            </div>
            <p>
              Selecting forecasts published after the decision cutoff causes <strong className="text-[#1F2925]">lookahead bias</strong> (evaluating decisions using future information unavailable to the desk at trade execution time).
            </p>
          </CardContent>
        </Card>

        {/* Timestamps & Semantics */}
        <Card className="border-[#C4D1C9] bg-white shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-blue-50 text-blue-700">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-base text-[#1F2925]">Publication vs Delivery Semantics</CardTitle>
                <CardDescription className="text-xs text-[#5A6B64]">Distinguishing time coordinates</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-[#5A6B64] leading-relaxed">
            <p>
              Every forecast observation has two distinct temporal coordinates:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li>
                <strong className="text-[#1F2925]">Publication Time (<code className="font-mono text-[11px]">publish_time</code>):</strong> When the forecast was computed and issued by the forecasting model onto the Elexon platform.
              </li>
              <li>
                <strong className="text-[#1F2925]">Delivery Start Time (<code className="font-mono text-[11px]">start_time</code>):</strong> The physical hour during which power generation is delivered into the GB transmission system.
              </li>
            </ul>
            <div className="rounded-md border border-blue-200 bg-blue-50/50 p-2.5 text-[11px] text-blue-900">
              <Calendar className="inline h-3.5 w-3.5 mr-1 text-blue-700 -mt-0.5" />
              <strong>Lead Time / Horizon:</strong> Computed as <code className="font-mono">horizon_hours = (start_time - cutoff)</code>. For a 10:00 cutoff on D-1, delivery hours 00:00 to 23:00 on D represent horizons from 14h to 37h.
            </div>
          </CardContent>
        </Card>

        {/* Data Ingestion & Alignment */}
        <Card className="border-[#C4D1C9] bg-white shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-emerald-50 text-[#174D3E]">
                <Layers className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-base text-[#1F2925]">Hourly Alignment of Elexon Datasets</CardTitle>
                <CardDescription className="text-xs text-[#5A6B64]">Reconciling 30-min actuals with 60-min forecasts</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-[#5A6B64] leading-relaxed">
            <p>
              The application ingests two official Elexon BMRS datasets:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li><strong className="text-[#1F2925]">FUELHH (WIND):</strong> Half-hourly settlement period actual generation (48 periods per standard settlement day).</li>
              <li><strong className="text-[#1F2925]">WINDFOR:</strong> Hourly national wind generation forecasts.</li>
            </ul>
            <div className="rounded-md border border-[#C4D1C9] bg-[#F2F5F3] p-3 text-[11px] font-mono text-[#1F2925]">
              <div className="font-semibold text-[#174D3E]">Aggregation Formula:</div>
              <div>Actual_Hourly(h) = (SP_{"{2h-1}"} + SP_{"{2h}"}) / 2.0</div>
              <div className="text-[10px] text-[#5A6B64] mt-1 font-sans">
                Taking the arithmetic mean of the two half-hour MW generation rates preserves both average power (MW) and cumulative energy delivered (MWh = MW × 1h = SP1 × 0.5h + SP2 × 0.5h).
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Commercial Trading Impact */}
        <Card className="border-[#C4D1C9] bg-white shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-amber-50 text-amber-700">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-base text-[#1F2925]">Commercial Trading & Imbalance Impact</CardTitle>
                <CardDescription className="text-xs text-[#5A6B64]">Implications of forecast error for buyers</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs text-[#5A6B64] leading-relaxed">
            <p>
              Signed error is defined as <strong className="text-[#1F2925]">Error = Forecast − Actual</strong>.
            </p>
            <div className="space-y-2">
              <div className="p-2 rounded bg-red-50/60 border border-red-200 text-[11px]">
                <strong className="text-red-900">Over-Forecasting (Error &gt; 0):</strong> The buyer anticipates abundant wind and under-contracts thermal/baseload volume. When actual wind falls short, the buyer is short power in real-time, facing costly <em className="text-red-800">System Buy Price (SBP)</em> cash-out exposure.
              </div>
              <div className="p-2 rounded bg-amber-50/60 border border-amber-200 text-[11px]">
                <strong className="text-amber-900">Under-Forecasting (Error &lt; 0):</strong> The buyer over-contracts power day-ahead. Excess wind results in long imbalance positions, often cashed out at discounted <em className="text-amber-800">System Sell Price (SSP)</em> or negative prices.
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Metrics Mathematical Definitions */}
      <Card className="border-[#C4D1C9] bg-white shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-[#174D3E]/10 text-[#174D3E]">
              <Calculator className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base text-[#1F2925]">Standard Statistical Metrics</CardTitle>
              <CardDescription className="text-xs text-[#5A6B64]">Precise mathematical formulation</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-3.5 rounded-lg border border-[#C4D1C9] bg-[#F2F5F3]">
              <div className="text-xs font-bold text-[#1F2925]">Mean Absolute Error (MAE)</div>
              <div className="mt-1 font-mono text-[11px] text-[#174D3E]">
                (1/N) × ∑ |Forecast_i − Actual_i|
              </div>
              <p className="mt-1.5 text-[11px] text-[#5A6B64]">
                Measures average magnitude of prediction error in MW without penalizing outliers disproportionately.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-[#C4D1C9] bg-[#F2F5F3]">
              <div className="text-xs font-bold text-[#1F2925]">Root Mean Square Error (RMSE)</div>
              <div className="mt-1 font-mono text-[11px] text-[#174D3E]">
                √[ (1/N) × ∑ (Forecast_i − Actual_i)² ]
              </div>
              <p className="mt-1.5 text-[11px] text-[#5A6B64]">
                Penalizes large extreme misses quadratically. Key metric for evaluating reserve margin stress.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-[#C4D1C9] bg-[#F2F5F3]">
              <div className="text-xs font-bold text-[#1F2925]">Mean Bias Error</div>
              <div className="mt-1 font-mono text-[11px] text-[#174D3E]">
                (1/N) × ∑ (Forecast_i − Actual_i)
              </div>
              <p className="mt-1.5 text-[11px] text-[#5A6B64]">
                Signed direction of systematic deviation. Positive values indicate persistent over-estimation of wind.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-[#C4D1C9] bg-[#F2F5F3]">
              <div className="text-xs font-bold text-[#1F2925]">WAPE</div>
              <div className="mt-1 font-mono text-[11px] text-[#174D3E]">
                (∑ |Error_i| / ∑ Actual_i) × 100%
              </div>
              <p className="mt-1.5 text-[11px] text-[#5A6B64]">
                Weighted Absolute Percentage Error avoids division by zero on low generation hours. Explicitly undefined if actuals sum to 0.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-[#C4D1C9] bg-[#F2F5F3]">
              <div className="text-xs font-bold text-[#1F2925]">Percentiles (P50, P90, P95)</div>
              <div className="mt-1 font-mono text-[11px] text-[#174D3E]">
                Percentile(|Error|, p)
              </div>
              <p className="mt-1.5 text-[11px] text-[#5A6B64]">
                Non-parametric tail risk metrics: 90% of hours have an error lower than P90. Essential for risk managers sizing options.
              </p>
            </div>

            <div className="p-3.5 rounded-lg border border-[#C4D1C9] bg-[#F2F5F3]">
              <div className="text-xs font-bold text-[#1F2925]">Coverage Ratio</div>
              <div className="mt-1 font-mono text-[11px] text-[#174D3E]">
                (N_evaluated / N_expected) × 100%
              </div>
              <p className="mt-1.5 text-[11px] text-[#5A6B64]">
                Verification metric verifying data integrity: tracks matching forecast and actual pairs across all 24 hours of each day.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dataset & Architecture Footnote */}
      <div className="rounded-xl border border-[#C4D1C9] bg-white p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Database className="h-6 w-6 text-[#174D3E] shrink-0" />
          <div>
            <div className="text-sm font-bold text-[#1F2925]">Verified Production Data Coverage</div>
            <div className="text-xs text-[#5A6B64]">
              January 2026 dataset: 744 target hours evaluated across 31 decision days with 100% data completeness.
            </div>
          </div>
        </div>
        <Badge variant="outline" className="text-xs font-mono text-[#174D3E] border-[#174D3E]/30 bg-[#174D3E]/5">
          Zero Synthetic Data
        </Badge>
      </div>
    </div>
  );
}