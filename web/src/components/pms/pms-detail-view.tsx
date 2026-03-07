"use client";

import useSWR from "swr";
import { usePmsDetail } from "@/hooks/use-pms-detail";
import { fetchPmsHoldings } from "@/lib/pms-api";
import { PmsKpiStrip } from "./pms-kpi-strip";
import { PmsNavChart } from "./pms-nav-chart";
import { PmsPerformanceTable } from "./pms-performance-table";
import { PmsDrawdownChart } from "./pms-drawdown-chart";
import { PmsWinLoss } from "./pms-win-loss";
import { PmsRiskScorecard } from "./pms-risk-scorecard";
import { PmsMethodology } from "./pms-methodology";
import { PmsUploadDialog } from "./pms-upload-dialog";
import { AllocationChart } from "@/components/portfolio/allocation-chart";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ArrowLeft } from "lucide-react";

interface PmsDetailViewProps {
  id: number;
  name: string;
  description: string | null;
  benchmark: string;
  onBack: () => void;
}

export function PmsDetailView({ id, name, description, benchmark, onBack }: PmsDetailViewProps) {
  const { summary, summaryLoading, metrics, metricsAsOf, refresh } = usePmsDetail(id);
  const { data: holdingsData } = useSWR(
    `pms-holdings-${id}`,
    () => fetchPmsHoldings(id),
    { refreshInterval: 300_000 }
  );

  // Loading state
  if (summaryLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-80 rounded-xl" />
      </div>
    );
  }

  // No PMS data yet — show empty state with upload
  if (summary === null) {
    return (
      <div className="space-y-4 sm:space-y-6">
        <PmsHeader
          name={name}
          description={description}
          benchmark={benchmark}
          onBack={onBack}
          portfolioId={id}
          onUploaded={refresh}
        />
        <EmptyState
          title="No PMS data yet"
          description="Upload a NAV report from your PMS broker to get started with analytics."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <PmsHeader
        name={name}
        description={description}
        benchmark={benchmark}
        onBack={onBack}
        portfolioId={id}
        onUploaded={refresh}
      />

      {/* KPI Strip */}
      <PmsKpiStrip summary={summary} />

      {/* NAV Chart */}
      <PmsNavChart portfolioId={id} />

      {/* Performance Table */}
      <PmsPerformanceTable metrics={metrics} asOfDate={metricsAsOf} />

      {/* Current Portfolio Allocation */}
      {holdingsData && (holdingsData.by_stock.length > 0 || holdingsData.by_sector.length > 0) && (
        <AllocationChart byStock={holdingsData.by_stock} bySector={holdingsData.by_sector} />
      )}

      {/* Drawdown Chart */}
      <PmsDrawdownChart portfolioId={id} />

      {/* Risk Management Scorecard */}
      <PmsRiskScorecard portfolioId={id} />

      {/* Win/Loss Analysis */}
      <PmsWinLoss portfolioId={id} />

      {/* Methodology */}
      <PmsMethodology />
    </div>
  );
}

// ─── Header ──────────────────────────────────────────────

function PmsHeader({
  name, description, benchmark, onBack, portfolioId, onUploaded,
}: {
  name: string;
  description: string | null;
  benchmark: string;
  onBack: () => void;
  portfolioId: number;
  onUploaded: () => void;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
        <Button variant="ghost" size="sm" onClick={onBack} className="self-start">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">{name}</h1>
            <Badge className="bg-teal-100 text-teal-700 text-[10px]">PMS</Badge>
            <Badge variant="outline" className="text-xs">
              vs {benchmark}
            </Badge>
          </div>
          {description && (
            <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">{description}</p>
          )}
        </div>
      </div>
      <PmsUploadDialog portfolioId={portfolioId} onUploaded={onUploaded} />
    </div>
  );
}
