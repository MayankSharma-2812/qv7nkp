import { useState } from "react";
import { Download, ArrowUpDown } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ForecastDecisionItem } from "@/api/types";
import { formatMW, formatUtcToLondon } from "@/lib/utils";

interface DecisionHourlyTableProps {
  forecasts: ForecastDecisionItem[];
  deliveryDate: string;
  decisionDate: string;
  cutoff: string;
}

export function DecisionHourlyTable({
  forecasts,
  deliveryDate,
  decisionDate,
  cutoff,
}: DecisionHourlyTableProps) {
  const [sortField, setSortField] = useState<"hour" | "abs_error" | "forecast" | "actual">("hour");
  const [sortAsc, setSortAsc] = useState<boolean>(true);

  const handleSort = (field: "hour" | "abs_error" | "forecast" | "actual") => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  const sorted = [...forecasts].sort((a, b) => {
    let diff = 0;
    if (sortField === "hour") {
      diff = a.delivery_hour_local - b.delivery_hour_local;
    } else if (sortField === "abs_error") {
      diff = (a.absolute_error_mw ?? -1) - (b.absolute_error_mw ?? -1);
    } else if (sortField === "forecast") {
      diff = (a.forecast_generation_mw ?? -1) - (b.forecast_generation_mw ?? -1);
    } else if (sortField === "actual") {
      diff = (a.actual_generation_mw ?? -1) - (b.actual_generation_mw ?? -1);
    }
    return sortAsc ? diff : -diff;
  });

  const handleExportCsv = () => {
    const headers = [
      "Interval_Europe_London",
      "Target_Start_UTC",
      "Forecast_MW",
      "Actual_MW",
      "Signed_Error_MW",
      "Absolute_Error_MW",
      "Publish_Time_UTC",
      "Horizon_Hours",
      "Status",
    ];

    const rows = forecasts.map((f) => [
      `${String(f.delivery_hour_local).padStart(2, "0")}:00`,
      f.target_start_utc,
      f.forecast_generation_mw !== null ? f.forecast_generation_mw : "",
      f.actual_generation_mw !== null ? f.actual_generation_mw : "",
      f.error_mw !== null ? f.error_mw : "",
      f.absolute_error_mw !== null ? f.absolute_error_mw : "",
      f.publish_time_utc || "",
      f.horizon_hours !== null ? f.horizon_hours.toFixed(1) : "",
      f.status,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `WindScope_${deliveryDate}_Cutoff_${cutoff.replace(/:/g, "")}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle>Hourly Delivery Interval Breakdown</CardTitle>
            <CardDescription>
              24 settlement hours for delivery date {deliveryDate} (Decision made {decisionDate} at {cutoff.slice(0, 5)} Europe/London)
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCsv}
            className="gap-2 self-start sm:self-auto text-xs"
          >
            <Download className="h-3.5 w-3.5 text-[#174D3E]" /> Export Hourly CSV
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border border-[#E2E0D8] overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead onClick={() => handleSort("hour")} className="cursor-pointer hover:text-[#141F1B]">
                  <div className="flex items-center gap-1">
                    Interval (London) <ArrowUpDown className="h-3 w-3" />
                  </div>
                </TableHead>
                <TableHead onClick={() => handleSort("forecast")} className="cursor-pointer hover:text-[#141F1B]">
                  <div className="flex items-center gap-1">
                    Forecast (MW) <ArrowUpDown className="h-3 w-3" />
                  </div>
                </TableHead>
                <TableHead onClick={() => handleSort("actual")} className="cursor-pointer hover:text-[#141F1B]">
                  <div className="flex items-center gap-1">
                    Actual (MW) <ArrowUpDown className="h-3 w-3" />
                  </div>
                </TableHead>
                <TableHead>Signed Error (MW)</TableHead>
                <TableHead onClick={() => handleSort("abs_error")} className="cursor-pointer hover:text-[#141F1B]">
                  <div className="flex items-center gap-1">
                    Abs Error (MW) <ArrowUpDown className="h-3 w-3" />
                  </div>
                </TableHead>
                <TableHead>Forecast Publish (UTC / London)</TableHead>
                <TableHead>Horizon</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((item) => {
                const isOver = (item.error_mw ?? 0) > 0;
                return (
                  <TableRow key={item.target_start_utc}>
                    <TableCell className="font-semibold text-[#141F1B]">
                      {String(item.delivery_hour_local).padStart(2, "0")}:00 - {String(item.delivery_hour_local + 1).padStart(2, "0")}:00
                    </TableCell>
                    <TableCell className="text-[#0D6E6E] font-medium">
                      {formatMW(item.forecast_generation_mw)}
                    </TableCell>
                    <TableCell className="text-[#E06D53] font-medium">
                      {formatMW(item.actual_generation_mw)}
                    </TableCell>
                    <TableCell>
                      {item.error_mw !== null ? (
                        <span
                          className={`font-semibold ${
                            isOver ? "text-[#E06D53]" : "text-[#0D6E6E]"
                          }`}
                        >
                          {item.error_mw > 0 ? "+" : ""}
                          {formatMW(item.error_mw)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="font-medium text-[#141F1B]">
                      {formatMW(item.absolute_error_mw)}
                    </TableCell>
                    <TableCell className="text-[11px] text-[#5A6B64]">
                      {item.publish_time_utc ? (
                        <>
                          <span className="font-medium text-[#141F1B]">{item.publish_time_utc.slice(11, 16)}Z</span> (London: {formatUtcToLondon(item.publish_time_utc)})
                        </>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-[11px] text-[#5A6B64]">
                      {item.horizon_hours !== null ? `${item.horizon_hours.toFixed(1)}h` : "—"}
                    </TableCell>
                    <TableCell>
                      {item.status === "MATCHED" ? (
                        <Badge variant="accent" className="text-[10px]">
                          Matched
                        </Badge>
                      ) : (
                        <Badge variant="warning" className="text-[10px]">
                          {item.status}
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
