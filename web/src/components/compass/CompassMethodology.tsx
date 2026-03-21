"use client";

const SECTIONS = [
  {
    title: "Relative Strength (RS) Score",
    content: `The RS Score measures how much a sector has outperformed or underperformed the benchmark index (NIFTY, NIFTY 100, or NIFTY 500) over the selected period.

**Calculation:**
1. Compute relative return = (Sector Return − Benchmark Return) over the chosen period (1M, 3M, 6M, or 12M)
2. Rank all sectors by relative return
3. Convert rank to percentile (0–100)

A score of 80 means the sector outperformed 80% of all other sectors relative to the benchmark. Simple, no weights, no complex formulas.`,
  },
  {
    title: "RS Momentum",
    content: `RS Momentum captures whether a sector's relative strength is improving or fading — the direction of change, not the level.

**Calculation:**
1. Compute today's RS Score
2. Compute the RS Score from 4 weeks ago (using the same method)
3. Momentum = Current RS Score − RS Score 4 weeks ago

**Positive momentum** = the sector is gaining relative strength (improving vs peers)
**Negative momentum** = the sector is losing relative strength (fading vs peers)

This is the single most important signal for timing. A sector can have a high RS Score but negative momentum — meaning it was strong but is now weakening.`,
  },
  {
    title: "Volume Trend",
    content: `Volume confirms whether price moves have institutional conviction behind them. We classify volume into 4 signals:

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **ACCUMULATION** | Volume rising + Price rising | Smart money buying — strongest confirmation |
| **WEAK RALLY** | Volume falling + Price rising | Rally on thin volume — unsustainable |
| **DISTRIBUTION** | Volume rising + Price falling | Smart money selling — danger signal |
| **WEAK DECLINE** | Volume falling + Price falling | Selling exhaustion — potential bottom |

**How it works:**
- Compare 20-day average volume vs 60-day average volume
- If 20d > 60d → volume is rising; otherwise falling
- Compare current price vs 20-day average price for direction
- Combine volume direction + price direction → signal`,
  },
  {
    title: "Quadrant Classification",
    content: `Every sector is placed into one of four quadrants based on two axes:

| Quadrant | RS Score | Momentum | Interpretation |
|----------|----------|----------|----------------|
| **LEADING** | > 50 | > 0 | Strong and getting stronger — best place to be |
| **WEAKENING** | > 50 | ≤ 0 | Was strong, now fading — watch for exits |
| **IMPROVING** | ≤ 50 | > 0 | Was weak, now gaining — watch for entries |
| **LAGGING** | ≤ 50 | ≤ 0 | Weak and getting weaker — avoid |

Sectors naturally rotate through these quadrants: IMPROVING → LEADING → WEAKENING → LAGGING → IMPROVING. The goal is to enter during IMPROVING and exit during WEAKENING.`,
  },
  {
    title: "Action Signals",
    content: `Each sector gets one of 4 clear actions based on its quadrant:

| Quadrant | Action | Meaning |
|----------|--------|---------|
| LEADING | **BUY** | Outperforming + gaining momentum — enter |
| WEAKENING | **HOLD** | Still outperforming but momentum fading — tighten stops |
| IMPROVING | **WATCH** | Underperforming but momentum turning up — wait |
| LAGGING | **SELL** | Underperforming + losing momentum — exit |

Simple rule: **BUY** what's strong and getting stronger. **SELL** what's weak and getting weaker. No ambiguity.`,
  },
  {
    title: "Stock Drill-Down",
    content: `When you click on a sector bubble, you see all constituent stocks within that sector ranked using the same RS methodology.

**Key difference at stock level:**
- Stocks are ranked against the **sector index** (not NIFTY) — this shows which stocks are leading within their sector
- Volume signals are computed per-stock using individual stock volume data
- Stop-loss levels are tighter for stocks (12%) vs sectors (8%)

This lets you find the strongest stocks within the strongest sectors — a double filter for quality.`,
  },
  {
    title: "Model Portfolio (Paper Trading)",
    content: `The system runs an autonomous paper-trading portfolio to validate the RS methodology in real-time.

**Rules:**
- Starting capital: ₹1 Crore
- Maximum 6 sector positions at any time (equal weight)
- Instruments: Sector ETFs (preferred) or top-ranked stocks

**Entry rules:**
- Enter when a sector signals **BUY** (LEADING + ACCUMULATION)
- Only if portfolio has capacity (< 6 positions)

**Exit rules:**
- Sector moves to **LAGGING** quadrant
- Sector is **WEAKENING** with **DISTRIBUTION** volume
- Stop-loss hit: 8% for sector ETFs, 12% for individual stocks
- Trailing stop: activates at 10% after 15% unrealized gain

**NAV tracking:**
- Daily NAV computed (base 100)
- Compared against NIFTY benchmark
- Compared against the fund manager's actual portfolio
- Performance metrics: total return, alpha, max drawdown, win rate

The model portfolio rebalances daily at 3:40 PM IST. Prices refresh every 15 minutes during market hours.`,
  },
  {
    title: "Data Sources",
    content: `All data is 100% real — fetched from live market sources. Zero synthetic or mock data.

| Data | Source | Frequency |
|------|--------|-----------|
| Index prices (135+ NSE indices) | nsetools (NSE API) | Every 15 min during market hours |
| Stock prices (all sector constituents) | yfinance | Every 15 min (5-day rolling window) |
| ETF prices (25 NSE-traded ETFs) | yfinance | Every 15 min (5-day rolling window) |
| Sector index constituents | NSE API | Daily |
| Historical prices (1Y backfill) | yfinance | On startup |

**Cache:** RS scores are cached for 15 minutes to avoid redundant computation. Cache is cleared on manual refresh.`,
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
          A simple, transparent framework — no black boxes, no complex weights.
          Three numbers per sector: RS Score, Momentum, and Volume Trend.
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
  // Skip separator row (row[1])
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
