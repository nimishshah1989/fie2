/** Sector Compass — API client */

import type {
  SectorRS,
  StockRS,
  ETFRS,
  PortfolioState,
  ModelTrade,
  NAVPoint,
  PerformanceMetrics,
  Period,
  PortfolioType,
} from "./compass-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchCompassSectors(
  base: string = "NIFTY",
  period: Period = "3M"
): Promise<SectorRS[]> {
  const res = await fetch(`${API}/api/compass/sectors?base=${base}&period=${period}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchCompassStocks(
  sectorKey: string,
  base: string = "NIFTY",
  period: Period = "3M"
): Promise<StockRS[]> {
  const res = await fetch(
    `${API}/api/compass/sectors/${sectorKey}/stocks?base=${base}&period=${period}`
  );
  if (!res.ok) return [];
  return res.json();
}

export async function fetchCompassETFs(
  base: string = "NIFTY",
  period: Period = "3M"
): Promise<ETFRS[]> {
  const res = await fetch(`${API}/api/compass/etfs?base=${base}&period=${period}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchModelPortfolio(portfolioType: PortfolioType = "etf_only"): Promise<PortfolioState | null> {
  const res = await fetch(`${API}/api/compass/model-portfolio?portfolio_type=${portfolioType}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchModelTrades(portfolioType: PortfolioType = "etf_only", limit = 50): Promise<ModelTrade[]> {
  const res = await fetch(`${API}/api/compass/model-portfolio/trades?portfolio_type=${portfolioType}&limit=${limit}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchModelNAV(portfolioType: PortfolioType = "etf_only", days = 365): Promise<NAVPoint[]> {
  const res = await fetch(`${API}/api/compass/model-portfolio/nav?portfolio_type=${portfolioType}&days=${days}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchModelPerformance(portfolioType: PortfolioType = "etf_only"): Promise<PerformanceMetrics | null> {
  const res = await fetch(`${API}/api/compass/model-portfolio/performance?portfolio_type=${portfolioType}`);
  if (!res.ok) return null;
  return res.json();
}

export async function refreshCompass(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API}/api/compass/refresh`, { method: "POST" });
  if (!res.ok) throw new Error("Refresh failed");
  return res.json();
}

// ─── Lab API ────────────────────────────────────────────────

export async function fetchLabStatus(): Promise<LabStatus | null> {
  const res = await fetch(`${API}/api/compass/lab/status`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchLabRuns(limit = 10): Promise<LabRun[]> {
  const res = await fetch(`${API}/api/compass/lab/runs?limit=${limit}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchLabConfigs(): Promise<RegimeConfig[]> {
  const res = await fetch(`${API}/api/compass/lab/configs`);
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function fetchLabRules(): Promise<DiscoveredRule[]> {
  const res = await fetch(`${API}/api/compass/lab/rules`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchLabDecisions(
  portfolioType: PortfolioType = "etf_only",
  limit = 50,
): Promise<LabDecision[]> {
  const res = await fetch(
    `${API}/api/compass/lab/decisions?portfolio_type=${portfolioType}&limit=${limit}`,
  );
  if (!res.ok) return [];
  return res.json();
}

export async function fetchLabAccuracy(
  portfolioType: PortfolioType = "etf_only",
): Promise<LabAccuracy | null> {
  const res = await fetch(
    `${API}/api/compass/lab/decisions/accuracy?portfolio_type=${portfolioType}`,
  );
  if (!res.ok) return null;
  return res.json();
}

export async function triggerLabSweep(sweepType: "full" | "focused" = "focused"): Promise<void> {
  await fetch(`${API}/api/compass/lab/sweep/trigger?sweep_type=${sweepType}`, { method: "POST" });
}

export async function triggerHistoryBackfill(): Promise<void> {
  await fetch(`${API}/api/compass/lab/backfill-history`, { method: "POST" });
}

// Lab types
export interface LabStatus {
  running: boolean;
  last_sweep: string | null;
  last_sweep_type: string | null;
  combos_tested_total: number;
  active_regime_configs: Record<string, Record<string, number>>;
  discovered_rules_count: number;
  next_sweep: string | null;
  historical_data: {
    status: string;
    n_days?: number;
    n_sectors?: number;
    date_range?: string;
    sectors?: string[];
    file_size_mb?: number;
  };
}

export interface LabRun {
  id: number;
  run_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  combos_tested: number | null;
  best_sharpe: number | null;
  data_range: string | null;
  notes: string | null;
}

export interface RegimeConfig {
  regime: string;
  params: {
    stop_loss_pct: number;
    trailing_trigger_pct: number;
    trailing_stop_pct: number;
    max_positions: number;
    min_rs_entry: number;
    min_holding_days: number;
    rs_period: string;
  };
  evidence: {
    sharpe: number | null;
    win_rate: number | null;
    n_trades: number | null;
    max_drawdown: number | null;
  };
  lab_run_id: number | null;
  updated_at: string | null;
}

export interface DiscoveredRule {
  id: number;
  discovered_date: string;
  condition: string;
  historical_n: number;
  historical_win_rate: number;
  baseline_win_rate: number;
  override_action: string;
  confidence: string;
  status: string;
  live_trades_since: number | null;
  live_win_rate: number | null;
}

export interface LabDecision {
  id: number;
  date: string;
  sector_key: string;
  decision: string;
  gates: { g1: boolean | null; g2: boolean | null; g3: boolean | null };
  rs_score: number | null;
  momentum: number | null;
  absolute_return: number | null;
  volume_signal: string | null;
  market_regime: string | null;
  pe_ratio: number | null;
  regime_config: string | null;
  reason: string | null;
  historical_precedent: { n: number; win_rate: number } | null;
  outcomes: {
    "5d": number | null;
    "20d": number | null;
    "60d": number | null;
    was_correct: boolean | null;
  };
}

export interface LabAccuracy {
  overall_accuracy: number;
  total_decisions: number;
  correct_decisions: number;
  by_decision: Record<string, { total: number; correct: number; accuracy: number }>;
  by_regime: Record<string, { total: number; correct: number; accuracy: number }>;
}
