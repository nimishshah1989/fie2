"use client";

import { useState, useCallback } from "react";
import { RefreshCw, Zap, Brain, Shield, Clock, CheckCircle, XCircle, AlertTriangle, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useLabStatus,
  useLabRuns,
  useLabConfigs,
  useLabRules,
  useLabDecisions,
  useLabAccuracy,
} from "@/hooks/use-compass";
import { triggerLabSweep, triggerHistoryBackfill } from "@/lib/compass-api";
import type { PortfolioType } from "@/lib/compass-types";

const REGIME_COLORS: Record<string, string> = {
  BULL: "bg-emerald-100 text-emerald-700",
  CAUTIOUS: "bg-amber-100 text-amber-700",
  CORRECTION: "bg-orange-100 text-orange-700",
  BEAR: "bg-red-100 text-red-700",
};

const DECISION_COLORS: Record<string, string> = {
  BUY: "bg-emerald-100 text-emerald-700",
  SELL: "bg-red-100 text-red-700",
  HOLD: "bg-blue-100 text-blue-700",
  SKIP: "bg-slate-100 text-slate-500",
};

const STATUS_ICONS: Record<string, typeof CheckCircle> = {
  COMPLETED: CheckCircle,
  RUNNING: Activity,
  FAILED: XCircle,
};

export function LabDashboard() {
  const [portfolioType, setPortfolioType] = useState<PortfolioType>("etf_only");
  const [triggering, setTriggering] = useState(false);
  const { status, isLoading: loadingStatus, mutate: mutateStatus } = useLabStatus();
  const { runs, isLoading: loadingRuns } = useLabRuns(5);
  const { configs, isLoading: loadingConfigs } = useLabConfigs();
  const { rules, isLoading: loadingRules } = useLabRules();
  const { decisions, isLoading: loadingDecisions } = useLabDecisions(portfolioType, 30);
  const { accuracy, isLoading: loadingAccuracy } = useLabAccuracy(portfolioType);

  const handleTriggerSweep = useCallback(async (type: "full" | "focused") => {
    setTriggering(true);
    try {
      await triggerLabSweep(type);
      setTimeout(() => mutateStatus(), 2000);
    } finally {
      setTriggering(false);
    }
  }, [mutateStatus]);

  if (loadingStatus) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Lab Status Header */}
      <LabStatusCard status={status} onTrigger={handleTriggerSweep} triggering={triggering} />

      {/* Historical Data Coverage */}
      <HistoricalDataCard status={status} />

      {/* Regime Configs — the brain of the system */}
      <RegimeConfigsCard configs={configs} loading={loadingConfigs} />

      {/* Discovered Rules */}
      <DiscoveredRulesCard rules={rules} loading={loadingRules} />

      {/* Decision Accuracy */}
      <AccuracyCard accuracy={accuracy} loading={loadingAccuracy} portfolioType={portfolioType} onTypeChange={setPortfolioType} />

      {/* Decision Log */}
      <DecisionLogCard decisions={decisions} loading={loadingDecisions} portfolioType={portfolioType} onTypeChange={setPortfolioType} />

      {/* Sweep History */}
      <SweepHistoryCard runs={runs} loading={loadingRuns} />
    </div>
  );
}

// ─── Lab Status Card ────────────────────────────────────────

function LabStatusCard({
  status,
  onTrigger,
  triggering,
}: {
  status: ReturnType<typeof useLabStatus>["status"];
  onTrigger: (type: "full" | "focused") => void;
  triggering: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-teal-600" />
          <h3 className="text-base font-semibold text-slate-900">Agentic Lab</h3>
          {status?.running ? (
            <span className="flex items-center gap-1.5 text-xs font-medium bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Running
            </span>
          ) : (
            <span className="text-xs font-medium bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">
              Idle
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => onTrigger("focused")} disabled={triggering} className="text-xs gap-1.5">
            <Zap className="h-3 w-3" /> Focused Sweep
          </Button>
          <Button variant="outline" size="sm" onClick={() => onTrigger("full")} disabled={triggering} className="text-xs gap-1.5">
            <RefreshCw className={`h-3 w-3 ${triggering ? "animate-spin" : ""}`} /> Full Sweep
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatBox label="Combos Tested" value={status?.combos_tested_total?.toLocaleString() ?? "0"} />
        <StatBox label="Rules Discovered" value={String(status?.discovered_rules_count ?? 0)} />
        <StatBox
          label="Last Sweep"
          value={status?.last_sweep ? new Date(status.last_sweep).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "Never"}
          sub={status?.last_sweep_type ?? ""}
        />
        <StatBox
          label="Next Sweep"
          value={status?.next_sweep ? new Date(status.next_sweep).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}
        />
      </div>
    </div>
  );
}

function StatBox({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <p className="text-xs text-slate-400 font-medium">{label}</p>
      <p className="text-lg font-bold font-mono text-slate-900 mt-0.5">{value}</p>
      {sub && <p className="text-[10px] text-slate-400 uppercase">{sub}</p>}
    </div>
  );
}

// ─── Historical Data Card ───────────────────────────────────

function HistoricalDataCard({ status }: { status: ReturnType<typeof useLabStatus>["status"] }) {
  const hd = status?.historical_data;
  if (!hd || hd.status !== "ready") return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="h-4 w-4 text-slate-400" />
        <h4 className="text-sm font-semibold text-slate-700">Historical Data Coverage</h4>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatBox label="Trading Days" value={hd.n_days?.toLocaleString() ?? "0"} />
        <StatBox label="Sectors" value={String(hd.n_sectors ?? 0)} />
        <StatBox label="Date Range" value={hd.date_range?.split(" to ")[0] ?? "—"} sub={`to ${hd.date_range?.split(" to ")[1] ?? ""}`} />
        <StatBox label="Data Size" value={`${hd.file_size_mb ?? 0} MB`} />
      </div>
      {hd.sectors && (
        <div className="mt-3 flex flex-wrap gap-1">
          {hd.sectors.map((s) => (
            <span key={s} className="text-[10px] bg-slate-50 text-slate-500 px-1.5 py-0.5 rounded">{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Regime Configs Card ────────────────────────────────────

function RegimeConfigsCard({ configs, loading }: { configs: ReturnType<typeof useLabConfigs>["configs"]; loading: boolean }) {
  if (loading) return <Skeleton className="h-48 w-full rounded-xl" />;
  if (!configs.length) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="h-4 w-4 text-teal-600" />
          <h4 className="text-sm font-semibold text-slate-700">Regime-Optimal Configs</h4>
        </div>
        <p className="text-sm text-slate-400">Lab is running its first sweep with historical data. Regime configs will appear once complete.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield className="h-4 w-4 text-teal-600" />
        <h4 className="text-sm font-semibold text-slate-700">Regime-Optimal Configs</h4>
        <span className="text-xs text-slate-400">Lab-derived parameters per market regime</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {configs.map((c) => (
          <div key={c.regime} className="border border-slate-100 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${REGIME_COLORS[c.regime] ?? "bg-slate-100 text-slate-600"}`}>
                {c.regime}
              </span>
              {c.evidence.sharpe !== null && (
                <span className="text-[10px] text-slate-400">Sharpe {c.evidence.sharpe?.toFixed(2)}</span>
              )}
            </div>

            <div className="space-y-1 text-xs">
              <ParamRow label="Stop Loss" value={`${c.params.stop_loss_pct}%`} />
              <ParamRow label="Trailing Trigger" value={`${c.params.trailing_trigger_pct}%`} />
              <ParamRow label="Trailing Stop" value={`${c.params.trailing_stop_pct}%`} />
              <ParamRow label="Max Positions" value={String(c.params.max_positions)} />
              <ParamRow label="Min RS" value={String(c.params.min_rs_entry)} />
              <ParamRow label="Min Hold" value={`${c.params.min_holding_days}d`} />
              <ParamRow label="RS Period" value={c.params.rs_period} />
            </div>

            {c.evidence.n_trades !== null && (
              <div className="mt-2 pt-2 border-t border-slate-50 flex justify-between text-[10px] text-slate-400">
                <span>{c.evidence.n_trades} trades</span>
                <span>{c.evidence.win_rate?.toFixed(0)}% win</span>
                <span>{c.evidence.max_drawdown?.toFixed(1)}% DD</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ParamRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-medium text-slate-700">{value}</span>
    </div>
  );
}

// ─── Discovered Rules Card ──────────────────────────────────

function DiscoveredRulesCard({ rules, loading }: { rules: ReturnType<typeof useLabRules>["rules"]; loading: boolean }) {
  if (loading) return <Skeleton className="h-32 w-full rounded-xl" />;
  if (!rules.length) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <h4 className="text-sm font-semibold text-slate-700">Discovered Rules</h4>
        </div>
        <p className="text-sm text-slate-400">No rules discovered yet. Rules emerge from patterns across thousands of simulated trades.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        <h4 className="text-sm font-semibold text-slate-700">Discovered Rules</h4>
        <span className="text-xs text-slate-400">{rules.length} patterns found</span>
      </div>

      <div className="space-y-2">
        {rules.map((r) => (
          <div key={r.id} className="border border-slate-100 rounded-lg p-3 flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                  r.status === "AUTO_APPLIED" ? "bg-emerald-100 text-emerald-700" :
                  r.status === "MONITORING" ? "bg-amber-100 text-amber-700" :
                  "bg-red-100 text-red-700"
                }`}>
                  {r.status}
                </span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  r.confidence === "HIGH" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                }`}>
                  {r.confidence}
                </span>
              </div>
              <p className="text-xs font-mono text-slate-700">{r.condition}</p>
              <p className="text-[10px] text-slate-400 mt-1">
                Action: <span className="font-medium">{r.override_action}</span>
                {" | "}{r.historical_n} trades, {r.historical_win_rate}% win (baseline: {r.baseline_win_rate}%)
              </p>
            </div>
            {r.live_trades_since !== null && r.live_trades_since > 0 && (
              <div className="text-right text-[10px] text-slate-400">
                <div>Live: {r.live_trades_since} trades</div>
                {r.live_win_rate !== null && <div>{r.live_win_rate}% win</div>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Accuracy Card ──────────────────────────────────────────

function AccuracyCard({
  accuracy,
  loading,
  portfolioType,
  onTypeChange,
}: {
  accuracy: ReturnType<typeof useLabAccuracy>["accuracy"];
  loading: boolean;
  portfolioType: PortfolioType;
  onTypeChange: (t: PortfolioType) => void;
}) {
  if (loading) return <Skeleton className="h-32 w-full rounded-xl" />;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CheckCircle className="h-4 w-4 text-teal-600" />
          <h4 className="text-sm font-semibold text-slate-700">Decision Accuracy</h4>
        </div>
        <PortfolioTypePills value={portfolioType} onChange={onTypeChange} />
      </div>

      {!accuracy || accuracy.total_decisions === 0 ? (
        <p className="text-sm text-slate-400">No decisions with outcomes yet. Accuracy will appear after 5+ trading days.</p>
      ) : (
        <div className="space-y-4">
          {/* Overall */}
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full border-4 border-teal-500 flex items-center justify-center">
              <span className="text-lg font-bold font-mono text-teal-700">{accuracy.overall_accuracy}%</span>
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700">{accuracy.correct_decisions}/{accuracy.total_decisions} correct</p>
              <p className="text-xs text-slate-400">Overall autonomous trader accuracy</p>
            </div>
          </div>

          {/* By decision type */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(accuracy.by_decision).map(([decision, stats]) => (
              <div key={decision} className="text-center">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${DECISION_COLORS[decision] ?? "bg-slate-100 text-slate-500"}`}>
                  {decision}
                </span>
                <p className="text-lg font-bold font-mono text-slate-900 mt-1">{stats.accuracy}%</p>
                <p className="text-[10px] text-slate-400">{stats.total} decisions</p>
              </div>
            ))}
          </div>

          {/* By regime */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(accuracy.by_regime).map(([regime, stats]) => (
              <div key={regime} className="text-center">
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${REGIME_COLORS[regime] ?? "bg-slate-100 text-slate-500"}`}>
                  {regime}
                </span>
                <p className="text-lg font-bold font-mono text-slate-900 mt-1">{stats.accuracy}%</p>
                <p className="text-[10px] text-slate-400">{stats.total} decisions</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Decision Log Card ──────────────────────────────────────

function DecisionLogCard({
  decisions,
  loading,
  portfolioType,
  onTypeChange,
}: {
  decisions: ReturnType<typeof useLabDecisions>["decisions"];
  loading: boolean;
  portfolioType: PortfolioType;
  onTypeChange: (t: PortfolioType) => void;
}) {
  if (loading) return <Skeleton className="h-48 w-full rounded-xl" />;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-400" />
          <h4 className="text-sm font-semibold text-slate-700">Autonomous Decision Log</h4>
          <span className="text-xs text-slate-400">{decisions.length} recent</span>
        </div>
        <PortfolioTypePills value={portfolioType} onChange={onTypeChange} />
      </div>

      {!decisions.length ? (
        <p className="text-sm text-slate-400">No decisions logged yet. The autonomous trader will log its first decisions at 3:40 PM IST.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">Date</th>
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">Sector</th>
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">Decision</th>
                <th className="text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">Gates</th>
                <th className="text-right text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">RS</th>
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">Regime</th>
                <th className="text-left text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">Reason</th>
                <th className="text-right text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">5d</th>
                <th className="text-right text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">20d</th>
                <th className="text-center text-[10px] font-semibold text-slate-400 uppercase tracking-wider pb-2">Correct?</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((d) => (
                <tr key={d.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2 font-mono text-slate-600">{d.date}</td>
                  <td className="py-2 font-medium text-slate-700">{d.sector_key}</td>
                  <td className="py-2">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${DECISION_COLORS[d.decision] ?? "bg-slate-100 text-slate-500"}`}>
                      {d.decision}
                    </span>
                  </td>
                  <td className="py-2 text-center font-mono">
                    <span className={d.gates.g1 ? "text-emerald-600" : "text-red-400"}>{d.gates.g1 ? "Y" : "N"}</span>
                    <span className={d.gates.g2 ? "text-emerald-600" : "text-red-400"}>{d.gates.g2 ? "Y" : "N"}</span>
                    <span className={d.gates.g3 ? "text-emerald-600" : "text-red-400"}>{d.gates.g3 ? "Y" : "N"}</span>
                  </td>
                  <td className="py-2 text-right font-mono">{d.rs_score?.toFixed(1) ?? "—"}</td>
                  <td className="py-2">
                    {d.market_regime && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${REGIME_COLORS[d.market_regime] ?? ""}`}>
                        {d.market_regime}
                      </span>
                    )}
                  </td>
                  <td className="py-2 text-slate-500 max-w-[200px] truncate" title={d.reason ?? ""}>{d.reason ?? ""}</td>
                  <td className={`py-2 text-right font-mono ${(d.outcomes["5d"] ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {d.outcomes["5d"] !== null ? `${d.outcomes["5d"]?.toFixed(1)}%` : "—"}
                  </td>
                  <td className={`py-2 text-right font-mono ${(d.outcomes["20d"] ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {d.outcomes["20d"] !== null ? `${d.outcomes["20d"]?.toFixed(1)}%` : "—"}
                  </td>
                  <td className="py-2 text-center">
                    {d.outcomes.was_correct === true && <CheckCircle className="h-3.5 w-3.5 text-emerald-500 inline" />}
                    {d.outcomes.was_correct === false && <XCircle className="h-3.5 w-3.5 text-red-500 inline" />}
                    {d.outcomes.was_correct === null && <span className="text-slate-300">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Sweep History Card ─────────────────────────────────────

function SweepHistoryCard({ runs, loading }: { runs: ReturnType<typeof useLabRuns>["runs"]; loading: boolean }) {
  if (loading) return <Skeleton className="h-32 w-full rounded-xl" />;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <RefreshCw className="h-4 w-4 text-slate-400" />
        <h4 className="text-sm font-semibold text-slate-700">Sweep History</h4>
      </div>

      {!runs.length ? (
        <p className="text-sm text-slate-400">No sweeps run yet.</p>
      ) : (
        <div className="space-y-2">
          {runs.map((r) => {
            const StatusIcon = STATUS_ICONS[r.status] ?? Activity;
            return (
              <div key={r.id} className="flex items-center gap-3 py-2 border-b border-slate-50 last:border-0">
                <StatusIcon className={`h-4 w-4 ${
                  r.status === "COMPLETED" ? "text-emerald-500" :
                  r.status === "RUNNING" ? "text-amber-500 animate-pulse" :
                  "text-red-500"
                }`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-slate-700">
                      {r.run_type} #{r.id}
                    </span>
                    <span className="text-[10px] text-slate-400">{r.data_range}</span>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {r.started_at && new Date(r.started_at).toLocaleString("en-IN")}
                    {r.completed_at && ` — ${new Date(r.completed_at).toLocaleString("en-IN")}`}
                  </div>
                </div>
                <div className="text-right">
                  {r.combos_tested !== null && (
                    <p className="text-xs font-mono text-slate-600">{r.combos_tested.toLocaleString()} combos</p>
                  )}
                  {r.best_sharpe !== null && r.best_sharpe > 0 && (
                    <p className="text-[10px] text-slate-400">Best Sharpe: {r.best_sharpe.toFixed(2)}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Portfolio Type Pills ───────────────────────────────────

function PortfolioTypePills({
  value,
  onChange,
}: {
  value: PortfolioType;
  onChange: (t: PortfolioType) => void;
}) {
  const types: PortfolioType[] = ["etf_only", "stock_etf", "stock_only"];
  const labels: Record<PortfolioType, string> = {
    etf_only: "ETF",
    stock_etf: "Blend",
    stock_only: "Stock",
  };

  return (
    <div className="flex gap-1">
      {types.map((t) => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
            value === t ? "bg-teal-600 text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
          }`}
        >
          {labels[t]}
        </button>
      ))}
    </div>
  );
}
