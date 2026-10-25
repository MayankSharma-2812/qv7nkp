# WindScope Demonstration Video Script

**Target Duration:** Maximum 10 minutes total  
- **Part 1 (Client Pitch & Product Demo):** 00:00 – 04:55 (Max 5 mins)  
- **Part 2 (Technical Architecture & Engineering Walkthrough):** 04:55 – 09:50 (Max 5 mins)  
**Deliverable Context:** Gridbricks Full Stack SWE Intern Challenge  
**Candidate Identifier:** Anonymous Submission (`qv7nkp`)  
**Data Scope:** January 2026 Historical Elexon BMRS Observations (744 evaluated settlement hours)

---

## Part 1: Client Pitch & Product Demo (00:00 – 04:55)

### Segment 1.1: The UK Power Buyer's Dilemma (00:00 – 01:10)
- **On Screen:** Open browser on `http://localhost:5173/`. Clean WindScope Decision Cockpit dashboard displayed. Mouse hovers over the header tags ("Jan 2026 Decisions", "UK National Grid").
- **Voiceover / Spoken:**
  > "Hello. If you are a commercial power buyer, a short-term power trader, or an energy procurement manager in Great Britain, you face significant volume uncertainty every morning. 
  > 
  > In the GB wholesale electricity market, day-ahead contracts for physical delivery on Day $D$ are auctioned and hedged on Day $D-1$ ahead of market gate closure. Wind is now the single most volatile marginal generator on the GB grid, frequently fluctuating by thousands of megawatts within hours.
  > 
  > When your trading desk prepares day-ahead positions, you rely on national wind generation forecasts published by Elexon BMRS. But here is the critical operational challenge: wind forecasts are continuously re-issued throughout the day. If your internal hedging decision cutoff is 10:00 AM on the day ahead, evaluating performance against forecasts published later in the day or intraday creates severe lookahead bias.
  > 
  > You need to know: *What was the exact forecast available to our desk at our decision cutoff, and how accurate did that forecast turn out to be across real physical delivery?*
  > 
  > This is **WindScope**—an analytical intelligence portal purpose-built to evaluate day-ahead wind forecasts under strict temporal anti-leakage rules."

### Segment 1.2: Decision Cockpit in Action (01:10 – 02:40)
- **On Screen:** 
  1. Select Decision Date: `2026-01-10` from dropdown.
  2. Select Cutoff: `10:00 Europe/London`.
  3. Show the resolved Delivery Date badge updating instantaneously to `2026-01-11`.
  4. Move cursor along the Recharts dual-axis chart: green curve (Forecast), terracotta curve (Actual Outturn), and bottom delta bars (Error MW).
  5. Scroll down to the Hourly Delivery Interval Table. Click "Signed Error" column header to sort by largest deviations. Click "Export Hourly CSV" and show the CSV download trigger.
- **Voiceover / Spoken:**
  > "Let's inspect the Decision Cockpit. We select our decision date—January 10th, 2026—and our decision cutoff, 10:00 AM Europe/London. Notice that 10:00 AM is our configurable evaluation benchmark assumption, reflecting typical pre-auction workflow.
  > 
  > WindScope immediately binds this to physical delivery day January 11th, across all 24 settlement hours.
  > 
  > Look at the KPI bar for January 11th: our day-ahead forecast called for 442.9 gigawatt-hours of wind, but actual delivered generation was 325.4 gigawatt-hours—a net over-forecast of 117.5 gigawatt-hours, with a daily Mean Absolute Error of 4,897 megawatts.
  > 
  > On our synchronized chart, the green line displays the exact forecast available at 10:00 AM on the tenth, while the orange line shows the outturn generation recorded by Elexon's FUELHH actuals. Notice the lower bar chart highlighting the hourly error delta.
  > 
  > Below, the hourly breakdown table displays the exact publication timestamp of every single forecast. For delivery hour 18:00 (6:00 to 7:00 PM), the model selected a forecast published at 09:30 UTC—prior to our 10:00 cutoff, with a lead time horizon of 32.5 hours. At that hour, the forecast was 20,293 megawatts while actual generation was 15,982 megawatts—a signed error of plus 4,311 megawatts.
  > 
  > Every row shows the lead-time horizon, signed deviation, and settlement status, with one-click CSV export for your quantitative desk."

### Segment 1.3: Accuracy Studio & Commercial Portfolio Implications (02:40 – 04:30)
- **On Screen:** Click sidebar link to navigate to **Accuracy Studio** (`/accuracy`). Show the 5 metric scorecards, diurnal curve chart, horizon degradation chart, and data completeness audit card.
- **Voiceover / Spoken:**
  > "Now let's switch to the Accuracy Studio, where we evaluate system-wide forecasting performance across the entire month of January 2026—representing 744 target hours across 31 decision days.
  > 
  > Here are the empirical findings:
  > - **Mean Absolute Error (MAE)** is 2,013 megawatts, representing average volume uncertainty.
  > - **Root Mean Square Error (RMSE)** is 2,506 megawatts. Because RMSE penalizes extreme errors quadratically, this gap highlights substantial tail-risk hours.
  > - Look at **Mean Signed Bias**: positive 1,730 megawatts. Across January 2026, the national wind forecast persistently over-estimated generation. Over 9.68 terawatt-hours were predicted versus 8.39 terawatt-hours delivered.
  > - In wholesale electricity procurement, persistent over-forecasting means an unhedged buyer risks anticipating abundant wind, potentially under-hedging baseload volume and facing imbalance cash-out exposure at System Buy Price (SBP). Conversely, under-forecasting risks spill at System Sell Price (SSP).
  > - **P90 Absolute Error** is 4,144 megawatts, meaning 10% of hours experienced misses larger than four gigawatts.
  > - **WAPE** is 17.8%, providing a normalized error metric that avoids division by zero.
  > 
  > To the right, our diurnal chart reveals when this error occurs: overnight hours from 03:00 to 05:00 experienced the highest MAE, exceeding 2,370 megawatts.
  > 
  > Finally, our verification card audits 100% data coverage—all 744 hours evaluated with zero fabricated points."

### Segment 1.4: Limitations & Decision Boundary (04:30 – 04:55)
- **On Screen:** Briefly scroll down to the Coverage and Auditing Footnote.
- **Voiceover / Spoken:**
  > "A vital note of commercial qualification: WindScope provides historical and evaluative clarity. It does not generate automatic financial trade execution orders, nor does it guarantee future wind accuracy. The 10:00 AM cutoff is a configurable evaluation benchmark, not a verified statutory exchange gate-closure. WindScope gives power buyers defensible, unpolluted data to size their volume hedges responsibly."

---

## Part 2: Technical Architecture & Engineering Walkthrough (04:55 – 09:50)

### Segment 2.1: System Architecture & Data Pipeline (04:55 – 06:15)
- **On Screen:** Open VS Code showing repository root. Display architecture diagram or directory tree in `README.md`.
- **Voiceover / Spoken:**
  > "Now for Part 2: technical architecture.
  > 
  > WindScope is structured as a decoupled full-stack application:
  > - The backend is built with Python 3.11, FastAPI, SQLAlchemy 2.0, and Pydantic schemas.
  > - The frontend is built with React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, and Recharts.
  > 
  > Data originates exclusively from official Elexon BMRS streaming APIs:
  > 1. `WINDFOR/stream`: hourly national forecast revisions.
  > 2. `FUELHH/stream` filtered to `fuelType=WIND`: half-hourly settlement observations.
  > 
  > Ingestion is strictly idempotent using SQLite primary keys and upserts. Our packaged historical database contains 1,488 actual half-hourly observations and 18,080 forecast revisions."

### Segment 2.2: Temporal Anti-Leakage & Resolution Alignment (06:15 – 07:25)
- **On Screen:** Open `backend/app/services/forecast_selection.py` and `backend/app/services/actuals.py`. Highlight lines implementing the cutoff inequality and the half-hourly arithmetic mean.
- **Voiceover / Spoken:**
  > "Let's inspect the two foundational engineering guarantees:
  > 
  > First, **Temporal Anti-Leakage**: in `forecast_selection.py`, we convert the user's decision date and cutoff time in Europe/London to UTC. We query all forecasts for target delivery hour $H$ with the strict invariant: `publish_time_utc <= cutoff_utc`. We then order by `publish_time_utc DESC` and take the latest eligible record. If a revision was published even one second past cutoff, it is strictly rejected.
  > 
  > Second, **Resolution Alignment**: `WINDFOR` forecasts are hourly (60-minute MW), while `FUELHH` actuals are half-hourly (30-minute MW for Settlement Periods 1 to 48). 
  > 
  > As shown in `actuals.py`, we aggregate by taking the arithmetic mean of the two half-hours: `(SP_1 + SP_2) / 2.0`. Because average power in MW multiplied by 1 hour equals energy in megawatt-hours, this exact formulation preserves both physical power rates and total cumulative energy."

### Segment 2.3: Automated Test Verification & Hand-Calculated Proof (07:25 – 08:25)
- **On Screen:** Split terminal: Run `pytest -v` in `backend/` (57 passed) and `npm test` in `frontend/` (16 passed). Total: 73 passed. Open `backend/tests/services/test_metrics.py`.
- **Voiceover / Spoken:**
  > "Let's run our automated test suite.
  > 
  > Running `pytest` executes 57 backend tests in 1.2 seconds, covering HTTP retry logic with Respx, cutoff edge conditions, leap boundaries, timezone transitions, and Pydantic validation.
  > 
  > Running `vitest` executes 16 frontend component and utility tests, verifying cross-month date mathematics, CSV generation, scorecards, and graceful undefined metric handling.
  > 
  > In `test_metrics.py`, every single statistic—MAE, RMSE, Bias, and WAPE—is tested against hand-calculated, hand-verifiable mathematical examples. Furthermore, if the sum of actuals is zero, WAPE is guarded to return `None` with an explicit reason, preventing mathematical division-by-zero or misleading zero displays."

### Segment 2.4: Production Containerization & CI Pipeline (08:25 – 09:20)
- **On Screen:** Open `docker-compose.yml`, `backend/Dockerfile`, and `.github/workflows/ci.yml`. Show `docker compose ps` and `curl http://localhost:8000/api/v1/ready`.
- **Voiceover / Spoken:**
  > "For production readiness, the entire system is containerized:
  > - The backend Dockerfile uses `python:3.11-slim`, runs as an unprivileged non-root user `appuser`, includes built-in curl health checks, and packages the verified historical SQLite dataset read-only. It dynamically binds to Render's `PORT` environment variable.
  > - The frontend Dockerfile uses a multi-stage build: building via Node 20 Alpine and serving through a lean Nginx Alpine container with gzip compression, security headers, SPA fallback routing, and a same-origin `/api/` reverse proxy.
  > - You can clone this repository on any clean machine and run `docker compose up --build` with zero local configuration.
  > 
  > In GitHub Actions, our CI workflow triggers on every push and pull request to `main`, running both test suites, TypeScript type checks, and Docker build validation."

### Segment 2.5: Conclusion & Technical Deliverables (09:20 – 09:50)
- **On Screen:** Show `qv7nkp/README.md` and the browser returning to WindScope.
- **Voiceover / Spoken:**
  > "To summarize: WindScope delivers high-fidelity, leakage-free wind forecast evaluation for UK electricity buyers. It combines rigorous temporal mathematics, resilient data persistence, and an intuitive, accessible user interface.
  > 
  > Full setup instructions, API specifications, and architectural documentation are in the root README. Thank you."

---

## Pre-Recording & Video Submission Checklist

1. **Resolution & Audio:** Record in 1080p (1920x1080) at 30 or 60 fps with clean, normalized microphone audio.
2. **Timing Gate:** Keep total video runtime strictly under 10 minutes (recommend ~09:30). Part 1 must finish before 05:00.
3. **YouTube Visibility:** Set video visibility to **Unlisted** (not Private, not Public).
4. **Anonymity Check:** Ensure terminal prompt, browser tabs, and desktop do not reveal full name, company, or personal credentials. Use anonymous repo name `qv7nkp`.
5. **No Synthetic Data:** Only use verified January 2026 historical Elexon data loaded in `gridbricks.db`.
