// ============================================================================
// Jhaveri Intelligence Platform — PMS API Client
// Fetches PMS NAV, metrics, drawdowns, transactions, and handles uploads
// ============================================================================

import type {
  PmsNavRecord,
  PmsMetric,
  DrawdownEvent,
  PmsTransactionRow,
  MonthlyReturn,
  PmsSummary,
  WinLossStats,
  RiskAnalytics,
} from "@/lib/pms-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchPmsNav(
  portfolioId: number,
  period: string = "all"
): Promise<PmsNavRecord[]> {
  const res = await fetch(`${API}/api/pms/${portfolioId}/nav?period=${period}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.nav_history || [];
}

export async function fetchPmsMetrics(
  portfolioId: number
): Promise<{ as_of_date: string | null; metrics: PmsMetric[] }> {
  const res = await fetch(`${API}/api/pms/${portfolioId}/metrics`);
  if (!res.ok) return { as_of_date: null, metrics: [] };
  const data = await res.json();
  return { as_of_date: data.as_of_date || null, metrics: data.metrics || [] };
}

export async function fetchPmsDrawdowns(
  portfolioId: number
): Promise<DrawdownEvent[]> {
  const res = await fetch(`${API}/api/pms/${portfolioId}/drawdowns`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.drawdowns || [];
}

export async function fetchPmsTransactions(
  portfolioId: number,
  script?: string,
  limit: number = 200,
  offset: number = 0
): Promise<{ total: number; transactions: PmsTransactionRow[] }> {
  let url = `${API}/api/pms/${portfolioId}/transactions?limit=${limit}&offset=${offset}`;
  if (script) url += `&script=${encodeURIComponent(script)}`;
  const res = await fetch(url);
  if (!res.ok) return { total: 0, transactions: [] };
  const data = await res.json();
  return { total: data.total || 0, transactions: data.transactions || [] };
}

export async function fetchPmsMonthlyReturns(
  portfolioId: number
): Promise<MonthlyReturn[]> {
  const res = await fetch(`${API}/api/pms/${portfolioId}/monthly-returns`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.monthly_returns || [];
}

export async function fetchPmsSummary(
  portfolioId: number
): Promise<PmsSummary | null> {
  const res = await fetch(`${API}/api/pms/${portfolioId}/summary`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchPmsWinLoss(
  portfolioId: number
): Promise<WinLossStats | null> {
  const res = await fetch(`${API}/api/pms/${portfolioId}/win-loss`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchPmsRiskAnalytics(
  portfolioId: number,
  period: string = "all",
): Promise<RiskAnalytics | null> {
  const res = await fetch(`${API}/api/pms/${portfolioId}/risk-analytics?period=${period}`);
  if (!res.ok) return null;
  return res.json();
}

export async function uploadPmsFiles(
  portfolioId: number,
  navFile: File,
  transactionFile?: File
): Promise<{
  status: string;
  new_nav_records: number;
  new_transactions: number;
  date_range: { start?: string; end?: string };
  transaction_error?: string;
}> {
  const formData = new FormData();
  formData.append("portfolio_id", portfolioId.toString());
  formData.append("nav_file", navFile);
  if (transactionFile) {
    formData.append("transaction_file", transactionFile);
  }

  const res = await fetch(`${API}/api/pms/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}
