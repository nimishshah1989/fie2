"use client";

import { useState, useEffect, useCallback } from "react";
import { FlaskConical, Clock, AlertCircle, RefreshCw } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { StrategyTable } from "@/components/simulator/StrategyTable";
import { SimulatorConfig } from "@/components/simulator/SimulatorConfig";
import { SimulatorChart } from "@/components/simulator/SimulatorChart";
import { SimulatorResults } from "@/components/simulator/SimulatorResults";
import { fetchBatch, runSimulation } from "@/lib/simulator-api";
import type { BatchResponse, SimulationResult, MetricInfo, MutualFund } from "@/lib/simulator-types";

const TOP_FUNDS: MutualFund[] = [
  { code: "119598", name: "SBI Bluechip Fund - Direct Growth", category: "Large Cap" },
  { code: "120503", name: "HDFC Flexi Cap Fund - Direct Growth", category: "Flexi Cap" },
  { code: "120505", name: "HDFC Mid-Cap Opportunities Fund - Direct Growth", category: "Mid Cap" },
  { code: "118989", name: "Parag Parikh Flexi Cap Fund - Direct Growth", category: "Flexi Cap" },
  { code: "120586", name: "ICICI Pru Bluechip Fund - Direct Growth", category: "Large Cap" },
  { code: "120587", name: "ICICI Pru Balanced Advantage Fund - Direct Growth", category: "BAF" },
  { code: "125497", name: "Nippon India Small Cap Fund - Direct Growth", category: "Small Cap" },
  { code: "120847", name: "SBI Small Cap Fund - Direct Growth", category: "Small Cap" },
  { code: "118834", name: "Axis Bluechip Fund - Direct Growth", category: "Large Cap" },
  { code: "119364", name: "Mirae Asset Large Cap Fund - Direct Growth", category: "Large Cap" },
  { code: "120716", name: "Kotak Flexicap Fund - Direct Growth", category: "Flexi Cap" },
  { code: "120578", name: "HDFC Balanced Advantage Fund - Direct Growth", category: "BAF" },
  { code: "122639", name: "HDFC Small Cap Fund - Direct Growth", category: "Small Cap" },
  { code: "125354", name: "Nippon India Large Cap Fund - Direct Growth", category: "Large Cap" },
  { code: "119062", name: "Axis Small Cap Fund - Direct Growth", category: "Small Cap" },
  { code: "120837", name: "SBI Equity Hybrid Fund - Direct Growth", category: "Hybrid" },
  { code: "118825", name: "Axis Midcap Fund - Direct Growth", category: "Mid Cap" },
  { code: "120179", name: "DSP Small Cap Fund - Direct Growth", category: "Small Cap" },
  { code: "135856", name: "Quant Small Cap Fund - Direct Growth", category: "Small Cap" },
  { code: "120594", name: "ICICI Pru Equity & Debt Fund - Direct Growth", category: "Hybrid" },
  { code: "118668", name: "UTI Nifty 50 Index Fund - Direct Growth", category: "Index" },
  { code: "147622", name: "Motilal Oswal Midcap Fund - Direct Growth", category: "Mid Cap" },
  { code: "120823", name: "SBI Large & Midcap Fund - Direct Growth", category: "Large & Mid Cap" },
  { code: "118632", name: "HDFC Top 100 Fund - Direct Growth", category: "Large Cap" },
  { code: "120684", name: "Kotak Emerging Equity Fund - Direct Growth", category: "Mid Cap" },
];

const ALL_METRICS: MetricInfo[] = [
  { key: "above_10ema", label: "Above 10 EMA" },
  { key: "above_21ema", label: "Above 21 EMA" },
  { key: "above_50ema", label: "Above 50 EMA" },
  { key: "above_200ema", label: "Above 200 EMA" },
  { key: "golden_cross", label: "Golden Cross" },
  { key: "macd_bull_cross", label: "MACD Bullish" },
  { key: "hit_52w_low", label: "Near 52W Low" },
  { key: "hit_52w_high", label: "Near 52W High" },
  { key: "roc_positive", label: "ROC Positive" },
  { key: "above_prev_month_high", label: "Above Prev Month High" },
];

const ALL_THRESHOLDS = [25, 50, 75, 100, 125];

export default function SimulatorPage() {
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Individual sim
  const [selectedFund, setSelectedFund] = useState<string | null>(null);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [running, setRunning] = useState(false);

  // Config state
  const [metric, setMetric] = useState("above_21ema");
  const [threshold, setThreshold] = useState(75);
  const [multiplier, setMultiplier] = useState(1);
  const [sipAmount, setSipAmount] = useState(10000);
  const [duration, setDuration] = useState(0);

  const loadBatch = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchBatch()
      .then((data) => setBatch(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadBatch(); }, [loadBatch]);

  const strategies = batch?.strategies ?? [];
  const s1 = strategies.find((s) => s.id === "strategy_1");
  const s2 = strategies.find((s) => s.id === "strategy_2");
  const rows1 = batch?.results?.filter((r) => r.strategy_id === "strategy_1") ?? [];
  const rows2 = batch?.results?.filter((r) => r.strategy_id === "strategy_2") ?? [];
  const hasData = batch?.results && batch.results.length > 0;

  const runSim = useCallback(async (fundCode: string) => {
    setRunning(true);
    setSimResult(null);
    setError(null);
    try {
      const startDate = duration > 0
        ? new Date(Date.now() - duration * 30 * 86400000).toISOString().split("T")[0]
        : "2018-01-01";
      const res = await runSimulation({
        fund_code: fundCode,
        metric_key: metric,
        stock_threshold: threshold,
        sip_amount: sipAmount,
        multiplier,
        start_date: startDate,
        duration_months: duration > 0 ? duration : null,
        sip_day: 1,
        cooloff_days: 30,
      });
      setSimResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setRunning(false);
    }
  }, [metric, threshold, sipAmount, multiplier, duration]);

  const handleFundSelect = useCallback((code: string) => {
    if (code === selectedFund) {
      setSelectedFund(null);
      setSimResult(null);
      return;
    }
    setSelectedFund(code);
    setSimResult(null);
    runSim(code);
  }, [selectedFund, runSim]);

  const selectedFundObj = TOP_FUNDS.find((f) => f.code === selectedFund);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <FlaskConical className="size-5 text-teal-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800">MF SIP Simulator</h1>
        </div>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Breadth-signal enhanced SIP vs regular SIP &middot;
          10 metrics &middot; 5 thresholds (25/50/75/100/125) &middot; 25 funds
        </p>
        {batch?.computed_at && (
          <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
            <Clock className="size-3" />
            Batch computed: {new Date(batch.computed_at).toLocaleString("en-IN")}
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-8 w-64 rounded-lg" />
          <Skeleton className="h-[300px] rounded-xl" />
        </div>
      )}

      {/* Strategy tables (only if batch data is ready) */}
      {!loading && hasData && s1 && (
        <StrategyTable strategy={s1} rows={rows1} onFundClick={handleFundSelect} selectedFund={selectedFund} />
      )}
      {!loading && hasData && s2 && (
        <StrategyTable strategy={s2} rows={rows2} onFundClick={handleFundSelect} selectedFund={selectedFund} />
      )}

      {/* Fund picker — always show when no batch data or no strategy table selection */}
      {!loading && !hasData && (
        <div className="space-y-4">
          {batch && !hasData && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertCircle className="size-5 text-amber-500 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-amber-800">
                    Batch comparison loading — data pipeline is still running
                  </p>
                  <p className="text-xs text-amber-600 mt-0.5">
                    Pick any fund below to run an individual simulation while batch results compute.
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={loadBatch} className="text-xs gap-1.5 shrink-0">
                <RefreshCw className="size-3" /> Retry
              </Button>
            </div>
          )}

          {/* Fund grid — always usable */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-sm font-semibold text-slate-700 mb-3">Select a fund to simulate</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {TOP_FUNDS.map((f) => (
                <button
                  key={f.code}
                  onClick={() => handleFundSelect(f.code)}
                  className={`text-left px-3 py-2.5 rounded-lg border text-xs transition-colors ${
                    selectedFund === f.code
                      ? "border-teal-500 bg-teal-50 text-teal-700"
                      : "border-slate-200 hover:border-teal-300 hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <p className="font-medium truncate">{f.name.replace(" - Direct Growth", "")}</p>
                  <span className="text-[10px] bg-slate-100 text-slate-500 rounded px-1.5 py-0.5 mt-1 inline-block">
                    {f.category}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Custom sim config + results */}
      {!loading && selectedFund && selectedFundObj && (
        <div className="space-y-3">
          <SimulatorConfig
            fund={selectedFundObj}
            strategy={s1 ?? { id: "custom", label: "Custom", description: "", metric, threshold, multiplier }}
            metric={metric} setMetric={setMetric}
            threshold={threshold} setThreshold={setThreshold}
            sipAmount={sipAmount} setSipAmount={setSipAmount}
            multiplier={multiplier} setMultiplier={setMultiplier}
            durationMonths={duration} setDurationMonths={setDuration}
            running={running}
            metrics={batch?.metrics ?? ALL_METRICS}
            thresholds={batch?.thresholds ?? ALL_THRESHOLDS}
            onRun={() => runSim(selectedFund)}
            onClose={() => { setSelectedFund(null); setSimResult(null); }}
          />

          {running && <Skeleton className="h-[400px] rounded-xl" />}

          {simResult && !running && (
            <>
              <SimulatorResults result={simResult} />
              <SimulatorChart timeline={simResult.timeline} triggerDates={simResult.trigger_dates} />
            </>
          )}
        </div>
      )}

      {/* Info */}
      {!loading && (
        <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500 leading-relaxed">
          <span className="font-semibold text-slate-600">How it works:</span>{" "}
          On each monthly SIP date, check how many Nifty 500 stocks meet the breadth condition.
          If count &le; threshold, invest an extra top-up SIP at that day&apos;s NAV.
          A 1-month cool-off prevents consecutive top-ups.
          Pick any metric (10 available) and threshold (25/50/75/100/125) to customize.
        </div>
      )}
    </div>
  );
}
