"use client";

import { Suspense, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { usePortfolios } from "@/hooks/use-portfolios";
import { usePortfolioDetail } from "@/hooks/use-portfolio-detail";
import { PortfolioSummaryCard } from "@/components/portfolio/portfolio-summary-card";
import { CreatePortfolioDialog } from "@/components/portfolio/create-portfolio-dialog";
import { TransactionDialog } from "@/components/portfolio/transaction-dialog";
import { HoldingsTable } from "@/components/portfolio/holdings-table";
import { TransactionTable } from "@/components/portfolio/transaction-table";
import { PortfolioKpiStrip } from "@/components/portfolio/portfolio-kpi-strip";
import { PortfolioChart } from "@/components/portfolio/portfolio-chart";
import { AllocationChart } from "@/components/portfolio/allocation-chart";
import { StatsRow } from "@/components/stats-row";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { formatPrice, formatPct } from "@/lib/utils";
import {
  Briefcase,
  ArrowLeft,
  Download,
  Plus,
  Clock,
} from "lucide-react";
import { getHoldingsExportURL, updateHoldingSymbol, archivePortfolio } from "@/lib/portfolio-api";
import { PmsDetailView } from "@/components/pms/pms-detail-view";
import type { Portfolio } from "@/lib/portfolio-types";

export default function PortfoliosPage() {
  return (
    <Suspense fallback={
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    }>
      <PortfoliosContent />
    </Suspense>
  );
}

function PortfoliosContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const selectedId = searchParams.get("id") ? parseInt(searchParams.get("id")!) : null;
  const { portfolios } = usePortfolios();

  if (selectedId) {
    const portfolio = portfolios.find((p) => p.id === selectedId);
    // If portfolio is PMS type, show PMS analytics dashboard
    if (portfolio?.portfolio_type === "pms") {
      return (
        <PmsDetailView
          id={selectedId}
          name={portfolio.name}
          description={portfolio.description}
          benchmark={portfolio.benchmark}
          onBack={() => router.push("/portfolios")}
        />
      );
    }
    return <PortfolioDetailView id={selectedId} onBack={() => router.push("/portfolios")} />;
  }

  return <PortfolioListView />;
}

// ─── List View ────────────────────────────────────────

function PortfolioListView() {
  const router = useRouter();
  const { portfolios, isLoading, mutate } = usePortfolios();

  // Edit state
  const [editTarget, setEditTarget] = useState<Portfolio | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  // Archive state
  const [archiveTarget, setArchiveTarget] = useState<Portfolio | null>(null);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const handleEdit = useCallback((portfolio: Portfolio) => {
    setEditTarget(portfolio);
    setEditDialogOpen(true);
  }, []);

  const handleArchive = useCallback((portfolio: Portfolio) => {
    setArchiveTarget(portfolio);
    setArchiveDialogOpen(true);
  }, []);

  const handleArchiveConfirm = useCallback(async () => {
    if (!archiveTarget) return;
    setArchiving(true);
    try {
      await archivePortfolio(archiveTarget.id);
      setArchiveDialogOpen(false);
      setArchiveTarget(null);
      mutate();
    } catch {
      // ignore
    } finally {
      setArchiving(false);
    }
  }, [archiveTarget, mutate]);

  const totalInvested = portfolios.reduce((s, p) => s + p.total_invested, 0);
  const totalCurrent = portfolios.reduce((s, p) => s + p.current_value, 0);
  const totalHoldings = portfolios.reduce((s, p) => s + p.num_holdings, 0);
  const overallReturn = totalInvested > 0
    ? ((totalCurrent - totalInvested) / totalInvested) * 100
    : 0;

  const stats = [
    { label: "Portfolios", value: portfolios.length },
    { label: "Total Holdings", value: totalHoldings },
    { label: "Total Invested", value: formatPrice(totalInvested) },
    { label: "Current Value", value: formatPrice(totalCurrent) },
    {
      label: "Overall Return",
      value: formatPct(overallReturn),
      color: overallReturn >= 0 ? "text-emerald-600" : "text-red-600",
    },
  ];

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Briefcase className="size-5 sm:size-6 text-primary" />
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">Model Portfolios</h1>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Create and manage model portfolio strategies
          </p>
        </div>
        <CreatePortfolioDialog onCreated={() => mutate()} />
      </div>

      {/* Stats */}
      {!isLoading && portfolios.length > 0 && <StatsRow stats={stats} />}

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      )}

      {/* Empty */}
      {!isLoading && portfolios.length === 0 && (
        <EmptyState
          title="No portfolios yet"
          description="Create your first model portfolio to start tracking strategy performance."
        />
      )}

      {/* Grid */}
      {!isLoading && portfolios.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {portfolios.map((p) => (
            <PortfolioSummaryCard
              key={p.id}
              portfolio={p}
              onClick={() => router.push(`/portfolios?id=${p.id}`)}
              onEdit={() => handleEdit(p)}
              onArchive={() => handleArchive(p)}
            />
          ))}
        </div>
      )}

      {/* Edit Portfolio Dialog */}
      <CreatePortfolioDialog
        onCreated={() => { setEditDialogOpen(false); setEditTarget(null); mutate(); }}
        open={editDialogOpen}
        onOpenChange={(v) => { setEditDialogOpen(v); if (!v) setEditTarget(null); }}
        editPortfolio={editTarget}
      />

      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Archive Portfolio</DialogTitle>
            <DialogDescription>
              Are you sure you want to archive{" "}
              <span className="font-semibold text-foreground">
                {archiveTarget?.name}
              </span>
              ? This will hide it from the active list.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center justify-end gap-3 pt-4">
            <Button
              variant="outline"
              onClick={() => setArchiveDialogOpen(false)}
              disabled={archiving}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleArchiveConfirm}
              disabled={archiving}
            >
              {archiving ? "Archiving..." : "Archive"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ─── Prices As Of timestamp display ──────────────────

function PricesAsOfBadge({ timestamp }: { timestamp: string | null }) {
  if (!timestamp) return null;

  try {
    const d = new Date(timestamp);
    const formatted = d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }) + " " + d.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

    return (
      <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
        <Clock className="h-3 w-3" />
        <span>Prices as of {formatted}</span>
      </div>
    );
  } catch {
    return null;
  }
}

// ─── Detail View ──────────────────────────────────────

function PortfolioDetailView({ id, onBack }: { id: number; onBack: () => void }) {
  const [activeTab, setActiveTab] = useState<"holdings" | "transactions">("holdings");
  const { detail, holdings, totals, pricesAsOf, transactions, performance, allocation, refresh } = usePortfolioDetail(id);

  // Transaction dialog state for pre-filled buy/sell from holding actions
  const [txnDialogOpen, setTxnDialogOpen] = useState(false);
  const [prefillTicker, setPrefillTicker] = useState("");
  const [prefillSector, setPrefillSector] = useState("");
  const [prefillTxnType, setPrefillTxnType] = useState<"BUY" | "SELL">("BUY");

  const handleTransactionComplete = useCallback(() => {
    setTxnDialogOpen(false);
    setPrefillTicker("");
    setPrefillSector("");
    refresh();
  }, [refresh]);

  const handleBuyMore = useCallback((ticker: string, sector: string | null) => {
    setPrefillTicker(ticker);
    setPrefillSector(sector || "");
    setPrefillTxnType("BUY");
    setTxnDialogOpen(true);
  }, []);

  const handleSell = useCallback((ticker: string) => {
    setPrefillTicker(ticker);
    setPrefillSector("");
    setPrefillTxnType("SELL");
    setTxnDialogOpen(true);
  }, []);

  const handleSymbolOverride = useCallback(async (holdingId: number, yfSymbol: string | null) => {
    await updateHoldingSymbol(id, holdingId, yfSymbol);
    refresh();
  }, [id, refresh]);

  if (!detail) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} className="self-start">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-bold text-foreground">{detail.name}</h1>
              <Badge variant="outline" className="text-xs">
                vs {detail.benchmark}
              </Badge>
            </div>
            {detail.description && (
              <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">{detail.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <TransactionDialog
            portfolioId={id}
            onCompleted={handleTransactionComplete}
            open={txnDialogOpen}
            onOpenChange={setTxnDialogOpen}
            prefillTicker={prefillTicker}
            prefillSector={prefillSector}
            prefillTxnType={prefillTxnType}
          />
        </div>
      </div>

      {/* KPI Strip */}
      {performance && <PortfolioKpiStrip performance={performance} />}

      {/* Performance Chart */}
      <PortfolioChart portfolioId={id} />

      {/* Allocation Charts */}
      {(allocation.by_stock.length > 0 || allocation.by_sector.length > 0) && (
        <AllocationChart byStock={allocation.by_stock} bySector={allocation.by_sector} />
      )}

      {/* Tab Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 border-b border-border pb-2">
        <div className="flex items-center gap-2">
          <Button
            variant={activeTab === "holdings" ? "default" : "ghost"}
            size="sm"
            className="text-xs"
            onClick={() => setActiveTab("holdings")}
          >
            Holdings ({holdings.length})
          </Button>
          <Button
            variant={activeTab === "transactions" ? "default" : "ghost"}
            size="sm"
            className="text-xs"
            onClick={() => setActiveTab("transactions")}
          >
            Transactions ({transactions.length})
          </Button>
        </div>

        <div className="sm:ml-auto flex items-center gap-3">
          {/* Prices timestamp */}
          {activeTab === "holdings" && <PricesAsOfBadge timestamp={pricesAsOf} />}

          {activeTab === "holdings" && (
            <a
              href={getHoldingsExportURL(id)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" size="sm" className="text-xs h-7 gap-1">
                <Download className="h-3 w-3" />
                Export
              </Button>
            </a>
          )}
        </div>
      </div>

      {/* Content */}
      {activeTab === "holdings" && (
        <>
          {holdings.length === 0 ? (
            <EmptyState
              title="No holdings yet"
              description="Add your first position using the 'Add Transaction' button above."
            />
          ) : (
            <HoldingsTable
              holdings={holdings}
              totals={totals}
              portfolioId={id}
              onBuyMore={handleBuyMore}
              onSell={handleSell}
              onSymbolOverride={handleSymbolOverride}
            />
          )}
        </>
      )}

      {activeTab === "transactions" && (
        <>
          {transactions.length === 0 ? (
            <EmptyState
              title="No transactions yet"
              description="Record your first BUY or SELL transaction."
            />
          ) : (
            <TransactionTable transactions={transactions} portfolioId={id} />
          )}
        </>
      )}
    </div>
  );
}
