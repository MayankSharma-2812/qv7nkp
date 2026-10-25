# WindScope: Frontend Design Specification
**Day-Ahead Wind Generation Intelligence & Forecast Accuracy Studio**

---

## 1. Executive Summary & Product Vision

**WindScope** is a specialized analytical application engineered for wholesale electricity traders and renewable power procurement desks operating in the UK day-ahead market. 

To determine residual thermal/dispatchable power procurement prior to market auction gate closure ($D-1$), trading desks rely on national wind generation forecasts. WindScope provides:
1. **Decision Cockpit**: What wind forecast was available at the exact decision cutoff on $D-1$ for delivery day $D$, and how did outturn physical generation actually materialize?
2. **Accuracy Studio**: Comprehensive quantitative accuracy evaluation (MAE, RMSE, Mean Bias, WAPE, Percentiles, Diurnal curves, Horizon degradation) across January 2026.
3. **Methodology Documentation**: Transparent documentation of data feeds (`FUELHH` vs `WINDFOR`), resolution alignment, temporal anti-leakage invariants, and statistical error metrics.

---

## 2. Visual Design System & Color Tokens

WindScope adopts a **premium, restrained editorial analytical aesthetic** tailored for high-density financial and energy power desks.

### 2.1 Palette Tokens (Light Theme First)

| Token Name | Hex Code | Semantic Role | Tailwind / CSS Variable |
| :--- | :--- | :--- | :--- |
| **Canvas Background** | `#F7F6F1` | Warm Ivory page canvas, reduces eye fatigue | `--background` |
| **Surface Card** | `#FFFFFF` | Crisp white elevated content card surfaces | `--card` |
| **Surface Subtle** | `#F0EFEA` | Secondary muted background for controls & badges | `--muted` |
| **Surface Accent** | `#DCE8DF` | Pale sage tint for highlighting and active states | `--accent` |
| **Brand Primary** | `#174D3E` | Deep British forest green, primary brand accent | `--primary` |
| **Typography Ink** | `#141F1B` | Deep dark slate ink for high-contrast legible headings | `--foreground` |
| **Typography Muted** | `#5A6B64` | Subdued slate-grey for labels, helper text, and axes | `--muted-foreground` |
| **Border Neutral** | `#E2E0D8` | Restrained neutral border line | `--border` |
| **Forecast Series** | `#0D6E6E` | Teal-cyan line/bar representing Day-Ahead Forecast | `--chart-forecast` |
| **Actual Series** | `#E06D53` | Terracotta coral line representing Outturn Actuals | `--chart-actual` |
| **Error Area Over** | `rgba(224, 109, 83, 0.15)` | Over-forecast highlight (wind shortfall risk) | `--chart-error-over` |
| **Error Area Under** | `rgba(13, 110, 110, 0.15)` | Under-forecast highlight (wind surplus) | `--chart-error-under` |
| **Warning Amber** | `#B45309` | Warning / advisory highlights | `--warning` |

### 2.2 Typography
- **Headings & Numerical Callouts**: System font stack with clean tabular numerals (`font-feature-settings: 'tnum' 1, 'cv02' 1`).
- **Body & Controls**: Clear, unpretentious sans-serif (`Inter`, system-ui, `-apple-system`, `sans-serif`) requiring zero external network roundtrips.

---

## 3. Layout & Navigation Hierarchy

### 3.1 Persistent Application Shell
```
+-----------------------------------------------------------------------------------------+
| [WindScope Logo]  |  Header: Page Title & Context Badge (January 2026 Historical)       |
|-------------------|---------------------------------------------------------------------|
| (Sidebar)         |  (Main Content Area - Max Width 1440px)                             |
| - Decision Cockpit|  +---------------------------------------------------------------+  |
| - Accuracy Studio |  | Control Filter Bar: Decision Date | Cutoff Time (Europe/London)|  |
| - Methodology     |  +---------------------------------------------------------------+  |
|                   |  | KPI Region (Key Metrics with Tooltips)                         |  |
|                   |  +---------------------------------------------------------------+  |
|                   |  | Primary Interactive Chart (Recharts + Custom Tooltip)          |  |
|                   |  +---------------------------------------------------------------+  |
|                   |  | Granular Breakdown Table / Diagnostics Panel                   |  |
| [System Status]   |  +---------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------+
```

### 3.2 Responsive Behavior
- **Desktop ($\ge 1024$px)**: 240px persistent left sidebar, stable 1440px max-width content canvas.
- **Tablet & Mobile ($< 1024$px)**: Compact top navigation bar with hamburger menu sliding a shadcn Sheet drawer. Filters stack vertically with touch-friendly 44px tap targets.

---

## 4. Page Breakdown & Component Architecture

### 4.1 Route 1: `/` (Decision Cockpit)
- **Purpose**: Answer "What was forecast at decision cutoff on $D-1$, and what actually materialized on delivery day $D$?"
- **Components**:
  - `DecisionControls`: Date picker (restricted to `2026-01-01` -> `2026-01-31`), Cutoff selector (`10:00 Europe/London` default, options for `09:00`, `10:00`, `11:00`, `12:00`). Displays corresponding delivery date badge.
  - `DecisionKpis`: 4-column KPI cards:
    - *Expected Wind Generation*: Total forecasted volume in GWh.
    - *Delivered Outturn Wind*: Total actual volume in GWh.
    - *Day Absolute Error*: Daily MAE in MW.
    - *Interval Coverage*: Matched hours (e.g. 24/24 hours, 100%).
  - `ForecastActualChart`: Large 420px Recharts time series with dual lines (Forecast MW vs Actual MW) and shaded error divergence. Custom tooltip shows interval local time, MW values, signed error ($F - A$), original `publishTime`, and lead horizon.
  - `DecisionHourlyTable`: Sortable shadcn table with columns for Interval, Forecast MW, Actual MW, Signed Error MW, Absolute Error MW, Forecast Publish Time, and Status. Includes a **CSV Export** action.

### 4.2 Route 2: `/accuracy` (Accuracy Studio)
- **Purpose**: Quantitative performance evaluation across configurable multi-day windows.
- **Components**:
  - `AccuracyControls`: Date range selector (`decision_date_from` to `decision_date_to`), Cutoff selector.
  - `MetricScorecards`: 5 key KPI cards:
    - **MAE (Mean Absolute Error)** in MW.
    - **RMSE (Root Mean Square Error)** in MW.
    - **Mean Signed Bias** in MW (highlighted in coral if over-forecasting, teal if under-forecasting).
    - **P90 Absolute Error** in MW (tail risk metric).
    - **WAPE (%)**: Volume-weighted percentage error.
  - `DiurnalChart`: Bar / Line chart showing diurnal error curve by Europe/London hour of day (00:00 to 23:00) using `/api/v1/accuracy/diurnal`.
  - `HorizonDegradationChart`: Categorical bar chart illustrating error magnitude across forecast lead time buckets (`< 14h`, `14-18h`, `18-24h`, `24-30h`, `30-36h`, `\ge 36h`) using `/api/v1/accuracy/distribution`.
  - `CoverageQualityCard`: Sample counts, matched-pair percentage, excluded counts, and methodology confirmation.

### 4.3 Route 3: `/methodology` (Methodology & Architecture)
- **Purpose**: Knowledge transfer for reviewers and power traders.
- **Sections**:
  - Domain context: Elexon BMRS datasets (`FUELHH` actuals vs `WINDFOR` forecasts).
  - Anti-leakage temporal gate closure rule ($\text{publish\_time\_utc} \le T_{\text{cutoff\_utc}}$).
  - Half-hour to hourly arithmetic mean aggregation ($\text{Actual}_{\text{hour}} = \frac{A_{00} + A_{30}}{2}$).
  - Statistical formulas: Signed error ($F - A$), MAE, RMSE, Bias, linear quantile percentile interpolation, and WAPE.
  - Assumptions vs verified facts table.

---

## 5. API-to-Component Mapping

| Endpoint | Frontend Component | Query Parameters | Response Used |
| :--- | :--- | :--- | :--- |
| `GET /api/v1/health` | `SystemStatusPanel` | None | `{ status, service, version }` |
| `GET /api/v1/ready` | `SystemStatusPanel` | None | `{ status, actual_observations_count, forecast_observations_count }` |
| `GET /api/v1/decisions/forecast` | `DecisionCockpit`, `ForecastActualChart`, `DecisionHourlyTable` | `decision_date`, `cutoff` | `DecisionForecastResponse` (24 hourly items) |
| `GET /api/v1/forecasts/series` | `DecisionCockpit` / Overview Series | `decision_date_from`, `decision_date_to`, `cutoff` | `ForecastSeriesResponse` |
| `GET /api/v1/accuracy/summary` | `AccuracyStudio`, `MetricScorecards`, `CoverageQualityCard` | `decision_date_from`, `decision_date_to`, `cutoff` | `AccuracySummaryResponse` (MAE, RMSE, Bias, P90, WAPE) |
| `GET /api/v1/accuracy/diurnal` | `DiurnalChart` | `decision_date_from`, `decision_date_to`, `cutoff` | `DiurnalResponse` (24 hourly rows) |
| `GET /api/v1/accuracy/distribution` | `HorizonDegradationChart` | `decision_date_from`, `decision_date_to`, `cutoff` | `DistributionResponse` (horizon buckets, quantiles) |

---

## 6. UX States: Loading, Error, Empty, and Stale Data

1. **Perceived Latency & TanStack Query Strategy**:
   - `staleTime: 5 * 60 * 1000` (5 minutes, matching backend `Cache-Control: max-age=300`).
   - `gcTime: 30 * 60 * 1000` (30 minutes).
   - `refetchOnWindowFocus: false` (historical data does not change in real time).
   - `AbortSignal` forwarded to fetch calls so obsolete requests cancel immediately when filters change.
2. **Skeleton Sizing**:
   - Explicit container heights for cards (`h-32`), charts (`h-[420px]`, `h-[320px]`), and table rows (`h-12`). Zero cumulative layout shift (CLS).
3. **Error Isolation**:
   - Independent queries wrapped in granular error boundaries with localized retry buttons. If diurnal query fails, summary metrics remain interactive.
4. **Empty State Guidance**:
   - Clear banner stating why no data is displayed with an instant button: "Reset to January 1, 2026 default".

---

## 7. Accessibility & Performance Strategy

- **WCAG 2.1 AA Compliance**: All typography and color pairs maintain $\ge 4.5:1$ contrast ratio against backgrounds.
- **Screen Reader Support**: Tables have structured `<thead>` and `<th>` scopes; charts include `accessibilityLayer` and accessible textual summary captions.
- **Keyboard Navigation**: All inputs, tabs, dropdowns, and buttons support standard `Tab`, `Space`, `Enter`, and arrow keys.
- **Bundle Optimization**: Tree-shaken Lucide icons, Vite code-splitting, zero external fonts.

---

## 8. Verification & Testing Plan

1. **Unit & Component Tests (`vitest` + React Testing Library)**:
   - Navigation and tab routing.
   - Date formatting and Europe/London timezone conversion.
   - Decision date vs delivery date offset verification.
   - Correct rendering of KPI cards from mock response fixtures.
   - Skeletons rendering during pending state, replacing with data upon resolution.
   - Error banner with retry trigger on HTTP 400/500 mock.
   - CSV export generation with correct headers and non-zero values.
2. **Integration Verification**:
   - Live smoke test against backend running at `http://localhost:8000`.
   - Inspection of screenshots across desktop (1440px) and mobile (375px).
