"use client";

const SECTIONS = [
  {
    title: "Three Gates — The Decision Framework",
    content: `Every sector, stock, and ETF is evaluated by three YES/NO questions. No weights, no scores — just binary conditions that anyone can verify.

| Gate | Question | How It's Measured |
|------|----------|-------------------|
| **G1** | Is it going up? | Absolute return > 0 over the selected period |
| **G2** | Is it beating the market? | RS Score > 0 (sector return − benchmark return) |
| **G3** | Is it getting stronger? | Momentum > 0 (RS today − RS 4 weeks ago) |

The combination of these three gates determines the action. No arbitrary thresholds or fuzzy scores.`,
  },
  {
    title: "Gate Combinations → Actions",
    content: `Each combination of pass/fail across the three gates maps to exactly one action:

| G1 (Rising?) | G2 (Beating Mkt?) | G3 (Strengthening?) | Action |
|:---:|:---:|:---:|---|
| YES | YES | YES | **BUY** — All conditions met. Enter position. |
| YES | YES | NO | **HOLD** — Outperforming but momentum fading. Tighten stops, no new entry. |
| YES | NO | YES | **WATCH (Emerging)** — Rising but still lagging market. Watch for RS > 0. |
| YES | NO | NO | **AVOID** — Rising but underperforming with fading momentum. Poor setup. |
| NO | YES | YES | **WATCH (Relative)** — Outperforming but price still falling. Watch for price turning positive. |
| NO | YES | NO | **SELL** — Falling and losing relative strength edge. |
| NO | NO | YES | **WATCH (Early)** — Early reversal signal. Needs RS and price both turning positive. |
| NO | NO | NO | **SELL** — Everything failing. Underperforming and falling. |`,
  },
  {
    title: "Volume & Regime Overrides",
    content: `Volume and market regime can override the base action — but only to downgrade, never upgrade:

**Volume Override:**
- DISTRIBUTION volume on a BUY → downgrades to **HOLD** ("smart money selling despite price strength")
- ACCUMULATION volume on a WATCH → adds a note that setup has higher probability

**Market Regime Override (based on NIFTY):**
- **BEAR** (drawdown > 15%) → BUY capped at HOLD. No new entries in a bear market.
- **CORRECTION** (drawdown > 8% or below 50 DMA with 3M return < -5%) → BUY requires volume to NOT be DISTRIBUTION or WEAK RALLY.
- **CAUTIOUS** (below 50 DMA) → No override, but regime is displayed.
- **BULL** → No override.`,
  },
  {
    title: "P/E Valuation Qualifier",
    content: `P/E does not change the action — it provides valuation context alongside the signal:

| P/E Range | Tag | Implication |
|-----------|-----|-------------|
| < 15 | **Value** | Cheap. Full conviction on BUY signals. |
| 15–25 | **Fair** | Normal valuation. No edge or concern. |
| 25–40 | **Stretched** | Premium valuation. BUY still valid but note the price. |
| > 40 | **Expensive** | Momentum may still work short-term, but entering at a premium. |

P/E is trailing 12-month (TTM) — factual, published by NSE, no analyst estimates needed.
A low P/E on a SELL signal is a value trap warning, not a reason to buy.`,
  },
  {
    title: "WATCH Variants Explained",
    content: `WATCH is not a single signal — it has three distinct variants, each watching for a specific trigger:

**WATCH (Emerging)** — G1✓ G2✗ G3✓
Sector is rising and gaining momentum, but still underperforming the benchmark.
**Trigger:** RS crossing above 0 — when sector return overtakes benchmark.
**What happens:** Upgrades to BUY. Classic breakout setup — sector catching up to market.

**WATCH (Relative)** — G1✗ G2✓ G3✓
Sector is outperforming and strengthening vs market, but absolute price is still negative.
**Trigger:** Absolute return turning positive — when sector price crosses its starting level.
**What happens:** Upgrades to BUY. Strongest horse in a weak market — first to turn when tide shifts.

**WATCH (Early)** — G1✗ G2✗ G3✓
Everything is down, but momentum just turned positive — earliest possible reversal signal.
**Trigger:** RS and absolute return both turning positive. Needs 2 gates to flip.
**What happens:** Upgrades to WATCH (Emerging) or WATCH (Relative) first, then eventually BUY.`,
  },
  {
    title: "How RS Score Is Calculated",
    content: `RS Score = (Sector Return − Benchmark Return) over the selected period.

**Example:**
- NIFTY IT returned +5% in 3 months
- NIFTY (benchmark) returned +8% in 3 months
- RS Score = 5% − 8% = **−3%** (underperforming)

Simple subtraction. Positive = outperforming. Negative = underperforming.
No percentiles, no normalization, no complex formulas.`,
  },
  {
    title: "How Momentum Is Calculated",
    content: `Momentum = RS Score today − RS Score 4 weeks ago.

This measures the **direction of change** in relative strength, not the level.

**Example:**
- RS Score today = +5%
- RS Score 4 weeks ago = +8%
- Momentum = 5% − 8% = **−3** (fading)

A sector can have a high RS Score but negative momentum — meaning it was strong but is now weakening. This is the most important signal for timing entries and exits.`,
  },
  {
    title: "Volume Trend",
    content: `Volume confirms whether price moves have institutional conviction behind them:

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **ACCUMULATION** | Volume rising + Price rising | Smart money buying — strongest confirmation |
| **WEAK RALLY** | Volume falling + Price rising | Rally on thin volume — unsustainable |
| **DISTRIBUTION** | Volume rising + Price falling | Smart money selling — danger signal |
| **WEAK DECLINE** | Volume falling + Price falling | Selling exhaustion — potential bottom |

Volume is measured by comparing 20-day average volume vs 60-day average volume, combined with price direction over the same period.`,
  },
  {
    title: "Same Framework at Every Level",
    content: `The exact same 3-gate logic applies at all levels:

| Level | G1: Going up? | G2: Beating what? | G3: Momentum vs what? |
|-------|--------------|-------------------|----------------------|
| **Sector** | Sector index return | Sector vs NIFTY | Sector RS change over 4w |
| **Stock** | Stock return | Stock vs its sector index | Stock RS change over 4w |
| **ETF** | ETF return | ETF vs NIFTY | ETF RS change over 4w |

Stocks compete against their sector, not the broad market. So within a BUY sector, individual stocks may be SELL (lagging their peers).`,
  },
  {
    title: "Data Sources",
    content: `All data is 100% real — fetched from live market sources.

| Data | Source | Frequency |
|------|--------|-----------|
| Index prices (135+ NSE indices) | nsetools (NSE API) | Every 15 min during market hours |
| Stock prices (sector constituents) | NSE API + yfinance fallback | Daily EOD |
| ETF prices | NSE API + yfinance fallback | Daily EOD |
| Sector index constituents | NSE API | Daily |
| Historical prices (1Y backfill) | NSE API + yfinance | On startup |
| P/E ratios | NSE published data | Cached 24h |`,
  },
];

export function CompassMethodology() {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-lg font-bold text-slate-900">
          How the Sector Compass Works
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          A deterministic, gate-based framework — no black boxes, no arbitrary weights.
          Three YES/NO questions determine every action.
        </p>
      </div>

      {SECTIONS.map((section) => (
        <div
          key={section.title}
          className="bg-white rounded-xl border border-slate-200 p-5"
        >
          <h3 className="text-sm font-semibold text-teal-700 mb-3">
            {section.title}
          </h3>
          <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line prose prose-sm prose-slate max-w-none
            prose-table:border prose-table:border-slate-200 prose-table:text-xs
            prose-th:bg-slate-50 prose-th:px-3 prose-th:py-1.5 prose-th:text-left prose-th:font-semibold prose-th:text-slate-600
            prose-td:px-3 prose-td:py-1.5 prose-td:border-t prose-td:border-slate-100
            prose-strong:text-slate-900">
            <MarkdownLite text={section.content} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Minimal markdown renderer for bold, tables, and line breaks */
function MarkdownLite({ text }: { text: string }) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Table detection
    if (line.trim().startsWith("|") && i + 1 < lines.length && lines[i + 1].trim().startsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      elements.push(<MdTable key={i} rows={tableLines} />);
      continue;
    }

    // Regular line with bold support
    if (line.trim() === "") {
      elements.push(<br key={i} />);
    } else {
      elements.push(
        <p key={i} className="mb-2">
          <BoldText text={line} />
        </p>
      );
    }
    i++;
  }

  return <>{elements}</>;
}

function BoldText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="font-semibold text-slate-900">
              {part.slice(2, -2)}
            </strong>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function MdTable({ rows }: { rows: string[] }) {
  const parseRow = (row: string) =>
    row
      .split("|")
      .filter((_, i, arr) => i > 0 && i < arr.length - 1)
      .map((cell) => cell.trim());

  const headers = parseRow(rows[0]);
  const dataRows = rows.slice(2).map(parseRow);

  return (
    <div className="overflow-x-auto my-3">
      <table className="w-full border border-slate-200 text-xs">
        <thead>
          <tr className="bg-slate-50">
            {headers.map((h, i) => (
              <th
                key={i}
                className="px-3 py-1.5 text-left font-semibold text-slate-600 border-b border-slate-200"
              >
                <BoldText text={h} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataRows.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className="px-3 py-1.5 border-t border-slate-100 text-slate-700"
                >
                  <BoldText text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
