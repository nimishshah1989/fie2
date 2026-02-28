// ============================================================================
// Jhaveri Intelligence Platform — Portfolio API
// Uses same server as alerts (port 8000 / same-origin in production)
// ============================================================================

import type {
  Portfolio,
  PortfolioDetail,
  PortfolioHoldingRow,
  HoldingsTotals,
  PortfolioTransactionRow,
  NAVDataPoint,
  PortfolioPerformance,
  AllocationItem,
  CreatePortfolioPayload,
  CreateTransactionPayload,
} from "@/lib/portfolio-types";

const PORTFOLIO_API = process.env.NEXT_PUBLIC_API_URL || "";

// ─── Portfolio CRUD ───────────────────────────────────

export async function fetchPortfolios(): Promise<Portfolio[]> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.portfolios || [];
}

export async function fetchPortfolioDetail(id: number): Promise<PortfolioDetail | null> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export async function createPortfolio(
  payload: CreatePortfolioPayload
): Promise<{ success: boolean; id?: number; error?: string }> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function updatePortfolio(
  id: number,
  payload: Partial<CreatePortfolioPayload>
): Promise<{ success: boolean }> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function archivePortfolio(
  id: number
): Promise<{ success: boolean }> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}`, {
    method: "DELETE",
  });
  return res.json();
}

// ─── Holdings ─────────────────────────────────────────

export async function fetchPortfolioHoldings(
  id: number
): Promise<{ holdings: PortfolioHoldingRow[]; totals: HoldingsTotals }> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}/holdings`);
  if (!res.ok) return { holdings: [], totals: emptyTotals() };
  const data = await res.json();
  return { holdings: data.holdings || [], totals: data.totals || emptyTotals() };
}

// ─── Transactions ─────────────────────────────────────

export async function fetchPortfolioTransactions(
  id: number,
  txnType?: string
): Promise<PortfolioTransactionRow[]> {
  let url = `${PORTFOLIO_API}/api/portfolios/${id}/transactions`;
  if (txnType) url += `?txn_type=${txnType}`;
  const res = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  return data.transactions || [];
}

export async function createTransaction(
  portfolioId: number,
  payload: CreateTransactionPayload
): Promise<{ success: boolean; error?: string; realized_pnl?: number }> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${portfolioId}/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

// ─── Performance & Analytics ──────────────────────────

export async function fetchPortfolioPerformance(
  id: number
): Promise<PortfolioPerformance | null> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}/performance`);
  if (!res.ok) return null;
  const data = await res.json();
  return data.performance || null;
}

export async function fetchNAVHistory(
  id: number,
  period: string = "all"
): Promise<NAVDataPoint[]> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}/nav-history?period=${period}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.nav_history || [];
}

export async function fetchAllocation(
  id: number
): Promise<{ by_stock: AllocationItem[]; by_sector: AllocationItem[] }> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}/allocation`);
  if (!res.ok) return { by_stock: [], by_sector: [] };
  const data = await res.json();
  return { by_stock: data.by_stock || [], by_sector: data.by_sector || [] };
}

// ─── NAV Computation ──────────────────────────────────

export async function computeNAV(
  id: number
): Promise<{ success: boolean }> {
  const res = await fetch(`${PORTFOLIO_API}/api/portfolios/${id}/compute-nav`, {
    method: "POST",
  });
  return res.json();
}

// ─── Export ───────────────────────────────────────────

export function getHoldingsExportURL(id: number): string {
  return `${PORTFOLIO_API}/api/portfolios/${id}/export/holdings`;
}

export function getTransactionsExportURL(id: number): string {
  return `${PORTFOLIO_API}/api/portfolios/${id}/export/transactions`;
}

// ─── Helpers ──────────────────────────────────────────

function emptyTotals(): HoldingsTotals {
  return {
    total_invested: 0,
    current_value: 0,
    unrealized_pnl: 0,
    unrealized_pnl_pct: 0,
    realized_pnl: 0,
    num_holdings: 0,
  };
}
