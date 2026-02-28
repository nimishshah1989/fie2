"use client";

import { Suspense, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { usePortfolios } from "@/hooks/use-portfolios";
import { usePortfolioDetail, useNAVHistory } from "@/hooks/use-portfolio-detail";
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
import { formatPrice, formatPct } from "@/lib/utils";
import {
  Briefcase,
  ArrowLeft,
  Download,
} from "lucide-react";
import { getHoldingsExportURL } from "@/lib/portfolio-api";

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

  if (selectedId) {
    return <PortfolioDetailView id={selectedId} onBack={() => router.push("/portfolios")} />;
  }

  return <PortfolioListView />;
}

// ─── List View ────────────────────────────────────────

function PortfolioListView() {
  const router = useRouter();
  const { portfolios, isLoading, mutate } = usePortfolios();

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Briefcase className="size-6 text-primary" />
            <h1 className="text-2xl font-bold text-foreground">Model Portfolios</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
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
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Detail View ──────────────────────────────────────

function PortfolioDetailView({ id, onBack }: { id: number; onBack: () => void }) {
  const [activeTab, setActiveTab] = useState<"holdings" | "transactions">("holdings");
  const { detail, holdings, totals, transactions, performance, allocation, refresh } = usePortfolioDetail(id);

  const handleTransactionComplete = useCallback(() => {
    refresh();
  }, [refresh]);

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{detail.name}</h1>
              <Badge variant="outline" className="text-xs">
                vs {detail.benchmark}
              </Badge>
            </div>
            {detail.description && (
              <p className="text-sm text-muted-foreground mt-0.5">{detail.description}</p>
            )}
          </div>
        </div>
        <TransactionDialog portfolioId={id} onCompleted={handleTransactionComplete} />
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
      <div className="flex items-center gap-2 border-b border-border pb-2">
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

        {activeTab === "holdings" && (
          <a
            href={getHoldingsExportURL(id)}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto"
          >
            <Button variant="outline" size="sm" className="text-xs h-7 gap-1">
              <Download className="h-3 w-3" />
              Export Holdings
            </Button>
          </a>
        )}
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
            <HoldingsTable holdings={holdings} totals={totals} />
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
