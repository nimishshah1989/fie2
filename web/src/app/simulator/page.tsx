"use client";

import { useState, useCallback } from "react";
import { FlaskConical, Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { SimulatorChart } from "@/components/simulator/SimulatorChart";
import { SimulatorResults } from "@/components/simulator/SimulatorResults";
import { fetchFunds, fetchMetrics, runSimulation } from "@/lib/simulator-api";
import type { MutualFund, BreadthMetric, SimulationResult } from "@/lib/simulator-types";
import { cn } from "@/lib/utils";

const DURATION_OPTIONS = [
  { label: "6 months", value: 6 },
  { label: "12 months", value: 12 },
  { label: "24 months", value: 24 },
  { label: "36 months", value: 36 },
  { label: "48 months", value: 48 },
  { label: "60 months", value: 60 },
  { label: "Till Date", value: 0 },
];

const MULTIPLIER_OPTIONS = [1, 1.5, 2, 3, 4, 5];

export default function SimulatorPage() {
  const [funds, setFunds] = useState<MutualFund[]>([]);
  const [shortMetrics, setShortMetrics] = useState<BreadthMetric[]>([]);
  const [broadMetrics, setBroadMetrics] = useState<BreadthMetric[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);

  // Form state
  const [fundCode, setFundCode] = useState("");
  const [metricKey, setMetricKey] = useState("");
  const [threshold, setThreshold] = useState(50);
  const [sipAmount, setSipAmount] = useState(10000);
  const [multiplier, setMultiplier] = useState(2);
  const [startDate, setStartDate] = useState("2023-01-01");
  const [durationMonths, setDurationMonths] = useState(0);
  const [sipDay, setSipDay] = useState(1);

  // Load funds + metrics on first interaction
  const loadData = useCallback(async () => {
    if (loaded) return;
    setLoading(true);
    try {
      const [fundsData, metricsData] = await Promise.all([fetchFunds(), fetchMetrics()]);
      setFunds(fundsData);
      setShortMetrics(metricsData.short_term);
      setBroadMetrics(metricsData.broad_trend);
      if (fundsData.length) setFundCode(fundsData[0].code);
      if (metricsData.short_term.length) setMetricKey(metricsData.short_term[0].key);
      setLoaded(true);
    } catch (e) {
      setError("Failed to load configuration data");
    } finally {
      setLoading(false);
    }
  }, [loaded]);

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await runSimulation({
        fund_code: fundCode,
        metric_key: metricKey,
        stock_threshold: threshold,
        sip_amount: sipAmount,
        multiplier,
        start_date: startDate,
        duration_months: durationMonths === 0 ? null : durationMonths,
        sip_day: sipDay,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setRunning(false);
    }
  }, [fundCode, metricKey, threshold, sipAmount, multiplier, startDate, durationMonths, sipDay]);

  return (
    <div className="space-y-5" onMouseEnter={loadData}>
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <FlaskConical className="size-5 text-teal-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800">MF SIP Simulator</h1>
        </div>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Compare regular SIP vs breadth-signal-enhanced SIP across top mutual funds
        </p>
      </div>

      {/* Configuration Panel */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-5">
        <p className="text-sm font-semibold text-slate-700">Simulation Parameters</p>

        {loading && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-16 rounded-lg" />)}
          </div>
        )}

        {loaded && (
          <>
            {/* Row 1: Fund + Metric */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">Mutual Fund</Label>
                <select
                  value={fundCode}
                  onChange={(e) => setFundCode(e.target.value)}
                  className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                >
                  {funds.map((f) => (
                    <option key={f.code} value={f.code}>
                      {f.name} ({f.category})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">Breadth Metric (Trigger Signal)</Label>
                <select
                  value={metricKey}
                  onChange={(e) => setMetricKey(e.target.value)}
                  className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                >
                  <optgroup label="Short-Term Metrics">
                    {shortMetrics.map((m) => (
                      <option key={m.key} value={m.key}>{m.label}</option>
                    ))}
                  </optgroup>
                  <optgroup label="Broad Trend Metrics">
                    {broadMetrics.map((m) => (
                      <option key={m.key} value={m.key}>{m.label}</option>
                    ))}
                  </optgroup>
                </select>
              </div>
            </div>

            {/* Row 2: Threshold + SIP Amount + Multiplier + SIP Day */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">
                  Stock Threshold (trigger if &le;)
                </Label>
                <Input
                  type="number"
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  min={1}
                  max={499}
                  className="font-mono"
                />
              </div>

              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">Monthly SIP (₹)</Label>
                <Input
                  type="number"
                  value={sipAmount}
                  onChange={(e) => setSipAmount(Number(e.target.value))}
                  min={500}
                  step={500}
                  className="font-mono"
                />
              </div>

              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">Extra SIP Multiplier</Label>
                <div className="flex gap-1.5 flex-wrap">
                  {MULTIPLIER_OPTIONS.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMultiplier(m)}
                      className={cn(
                        "px-2.5 py-1 rounded-md text-xs font-medium border transition-colors",
                        multiplier === m
                          ? "bg-teal-600 text-white border-teal-600"
                          : "bg-white text-slate-600 border-slate-200 hover:border-teal-400"
                      )}
                    >
                      {m}x
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">SIP Day of Month</Label>
                <Input
                  type="number"
                  value={sipDay}
                  onChange={(e) => setSipDay(Number(e.target.value))}
                  min={1}
                  max={28}
                  className="font-mono"
                />
              </div>
            </div>

            {/* Row 3: Start Date + Duration */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 items-end">
              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">Simulation Start Date</Label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="font-mono"
                />
              </div>

              <div>
                <Label className="text-xs text-slate-500 mb-1.5 block">Duration</Label>
                <select
                  value={durationMonths}
                  onChange={(e) => setDurationMonths(Number(e.target.value))}
                  className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                >
                  {DURATION_OPTIONS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <Button
                  onClick={handleRun}
                  disabled={running || !fundCode || !metricKey}
                  className="w-full bg-teal-600 text-white hover:bg-teal-700 gap-2"
                >
                  {running ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4" />
                      Run Simulation
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Info box */}
            <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500 leading-relaxed">
              <span className="font-semibold text-slate-600">How it works:</span>{" "}
              On each SIP date, the simulator checks if the selected breadth metric count
              (e.g., stocks above 10 EMA) is &le; your threshold. If triggered, an extra{" "}
              <span className="font-mono font-semibold text-teal-600">{multiplier}x</span> of
              your SIP amount (₹{sipAmount.toLocaleString("en-IN")}) is invested — buying more
              units at lower NAV. The result compares this enhanced strategy against a plain SIP.
            </div>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Running state */}
      {running && (
        <div className="space-y-4">
          <Skeleton className="h-[400px] rounded-xl" />
          <div className="grid grid-cols-2 gap-4">
            {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
          </div>
        </div>
      )}

      {/* Results */}
      {result && !running && (
        <>
          <SimulatorChart timeline={result.timeline} triggerDates={result.trigger_dates} />
          <SimulatorResults result={result} />
        </>
      )}

      {/* Empty state */}
      {!result && !running && !error && loaded && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <FlaskConical className="h-12 w-12 text-muted-foreground/40 mb-4" />
          <h3 className="text-lg font-semibold text-foreground">Configure & Run</h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-md">
            Set your parameters above and click &quot;Run Simulation&quot; to compare
            regular SIP vs breadth-enhanced SIP performance.
          </p>
        </div>
      )}
    </div>
  );
}
