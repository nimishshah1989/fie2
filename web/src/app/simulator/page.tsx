"use client";

import { useState, useEffect, useCallback } from "react";
import { FlaskConical, Clock, AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { StrategyTable } from "@/components/simulator/StrategyTable";
import { SimulatorConfig } from "@/components/simulator/SimulatorConfig";
import { SimulatorChart } from "@/components/simulator/SimulatorChart";
import { SimulatorResults } from "@/components/simulator/SimulatorResults";
import { fetchBatch, runSimulation } from "@/lib/simulator-api";
import type { BatchResponse, SimulationResult, MetricInfo } from "@/lib/simulator-types";

const TOP_FUNDS = [
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

export default function SimulatorPage() {
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-strategy interactive state
  const [selectedFund1, setSelectedFund1] = useState<string | null>(null);
  const [selectedFund2, setSelectedFund2] = useState<string | null>(null);
  const [simResult1, setSimResult1] = useState<SimulationResult | null>(null);
  const [simResult2, setSimResult2] = useState<SimulationResult | null>(null);
  const [running1, setRunning1] = useState(false);
  const [running2, setRunning2] = useState(false);

  // Editable params for each strategy
  const [metric1, setMetric1] = useState("above_21ema");
  const [threshold1, setThreshold1] = useState(75);
  const [multiplier1, setMultiplier1] = useState(1);
  const [sipAmount1, setSipAmount1] = useState(10000);
  const [duration1, setDuration1] = useState(0);

  const [metric2, setMetric2] = useState("above_200ema");
  const [threshold2, setThreshold2] = useState(100);
  const [multiplier2, setMultiplier2] = useState(2);
  const [sipAmount2, setSipAmount2] = useState(10000);
  const [duration2, setDuration2] = useState(0);

  const availableMetrics: MetricInfo[] = batch?.metrics ?? [
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
  const availableThresholds = batch?.thresholds ?? [25, 50, 75, 100, 125];

  useEffect(() => {
    fetchBatch()
      .then((data) => { setBatch(data); setError(null); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const strategies = batch?.strategies ?? [];
  const s1 = strategies.find((s) => s.id === "strategy_1");
  const s2 = strategies.find((s) => s.id === "strategy_2");
  const rows1 = batch?.results.filter((r) => r.strategy_id === "strategy_1") ?? [];
  const rows2 = batch?.results.filter((r) => r.strategy_id === "strategy_2") ?? [];

  const runSim = useCallback(async (
    strategyIdx: 1 | 2,
    fundCode: string,
    metricKey: string,
    threshold: number,
    multiplier: number,
    sipAmount: number,
    duration: number,
  ) => {
    const setRunning = strategyIdx === 1 ? setRunning1 : setRunning2;
    const setResult = strategyIdx === 1 ? setSimResult1 : setSimResult2;
    setRunning(true);
    setResult(null);
    try {
      const startDate = duration > 0
        ? new Date(Date.now() - duration * 30 * 86400000).toISOString().split("T")[0]
        : "2018-01-01";
      const res = await runSimulation({
        fund_code: fundCode,
        metric_key: metricKey,
        stock_threshold: threshold,
        sip_amount: sipAmount,
        multiplier,
        start_date: startDate,
        duration_months: duration > 0 ? duration : null,
        sip_day: 1,
        cooloff_days: 30,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setRunning(false);
    }
  }, []);

  const handleFundClick1 = useCallback((code: string) => {
    setSelectedFund1(code === selectedFund1 ? null : code);
    setSimResult1(null);
    if (code !== selectedFund1 && s1) {
      runSim(1, code, metric1, threshold1, multiplier1, sipAmount1, duration1);
    }
  }, [selectedFund1, s1, metric1, threshold1, multiplier1, sipAmount1, duration1, runSim]);

  const handleFundClick2 = useCallback((code: string) => {
    setSelectedFund2(code === selectedFund2 ? null : code);
    setSimResult2(null);
    if (code !== selectedFund2 && s2) {
      runSim(2, code, metric2, threshold2, multiplier2, sipAmount2, duration2);
    }
  }, [selectedFund2, s2, metric2, threshold2, multiplier2, sipAmount2, duration2, runSim]);

  const fund1 = TOP_FUNDS.find((f) => f.code === selectedFund1);
  const fund2 = TOP_FUNDS.find((f) => f.code === selectedFund2);

  const hasData = batch?.results && batch.results.length > 0;
  const isPipelinePending = batch && !batch.cached && !hasData;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <FlaskConical className="size-5 text-teal-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800">MF SIP Simulator</h1>
        </div>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Breadth-signal enhanced SIP vs regular SIP across top 25 mutual funds &middot;
          10 metrics &middot; 5 threshold levels &middot; 1-month cool-off
        </p>
        {batch?.computed_at && (
          <p className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
            <Clock className="size-3" />
            Last computed: {new Date(batch.computed_at).toLocaleString("en-IN")}
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* Pipeline pending state */}
      {!loading && isPipelinePending && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center space-y-2">
          <AlertCircle className="size-8 text-amber-500 mx-auto" />
          <h3 className="text-sm font-semibold text-amber-800">Data Pipeline Running</h3>
          <p className="text-xs text-amber-600 max-w-md mx-auto">
            The simulator is computing breadth metrics and fetching MF NAV data.
            This runs once on server startup and takes a few minutes. Refresh the page shortly.
          </p>
          {batch?.errors && batch.errors.length > 0 && (
            <p className="text-[10px] text-amber-500 mt-2">{batch.errors[0]}</p>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-8 w-64 rounded-lg" />
          <Skeleton className="h-[400px] rounded-xl" />
        </div>
      )}

      {/* Strategy 1 */}
      {!loading && hasData && s1 && (
        <div className="space-y-3">
          <StrategyTable
            strategy={s1}
            rows={rows1}
            onFundClick={handleFundClick1}
            selectedFund={selectedFund1}
          />

          {selectedFund1 && fund1 && (
            <div className="space-y-3">
              <SimulatorConfig
                fund={fund1} strategy={s1}
                metric={metric1} setMetric={setMetric1}
                threshold={threshold1} setThreshold={setThreshold1}
                sipAmount={sipAmount1} setSipAmount={setSipAmount1}
                multiplier={multiplier1} setMultiplier={setMultiplier1}
                durationMonths={duration1} setDurationMonths={setDuration1}
                running={running1}
                metrics={availableMetrics}
                thresholds={availableThresholds}
                onRun={() => runSim(1, selectedFund1, metric1, threshold1, multiplier1, sipAmount1, duration1)}
                onClose={() => { setSelectedFund1(null); setSimResult1(null); }}
              />
              {running1 && <Skeleton className="h-[400px] rounded-xl" />}
              {simResult1 && !running1 && (
                <>
                  <SimulatorChart timeline={simResult1.timeline} triggerDates={simResult1.trigger_dates} />
                  <SimulatorResults result={simResult1} />
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Strategy 2 */}
      {!loading && hasData && s2 && (
        <div className="space-y-3">
          <StrategyTable
            strategy={s2}
            rows={rows2}
            onFundClick={handleFundClick2}
            selectedFund={selectedFund2}
          />

          {selectedFund2 && fund2 && (
            <div className="space-y-3">
              <SimulatorConfig
                fund={fund2} strategy={s2}
                metric={metric2} setMetric={setMetric2}
                threshold={threshold2} setThreshold={setThreshold2}
                sipAmount={sipAmount2} setSipAmount={setSipAmount2}
                multiplier={multiplier2} setMultiplier={setMultiplier2}
                durationMonths={duration2} setDurationMonths={setDuration2}
                running={running2}
                metrics={availableMetrics}
                thresholds={availableThresholds}
                onRun={() => runSim(2, selectedFund2, metric2, threshold2, multiplier2, sipAmount2, duration2)}
                onClose={() => { setSelectedFund2(null); setSimResult2(null); }}
              />
              {running2 && <Skeleton className="h-[400px] rounded-xl" />}
              {simResult2 && !running2 && (
                <>
                  <SimulatorChart timeline={simResult2.timeline} triggerDates={simResult2.trigger_dates} />
                  <SimulatorResults result={simResult2} />
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Info */}
      {!loading && hasData && (
        <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500 leading-relaxed">
          <span className="font-semibold text-slate-600">How it works:</span>{" "}
          On each monthly SIP date, the simulator checks how many Nifty 500 stocks meet
          the breadth condition. If the count is at or below the threshold, an extra top-up
          SIP is invested at that day&apos;s NAV. A <span className="font-semibold text-teal-600">1-month cool-off</span>{" "}
          prevents consecutive top-ups within 30 days. Click any fund row to customize
          the metric, threshold, multiplier, and duration.
        </div>
      )}
    </div>
  );
}
