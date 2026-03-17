"use client";

import { useCallback, useState } from "react";
import { Globe } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { PageInfo } from "@/components/page-info";
import { GlobalBreadcrumb } from "@/components/global-pulse/global-breadcrumb";
import { GlobalHeatmap } from "@/components/global-pulse/global-heatmap";
import { GlobalIndexList } from "@/components/global-pulse/global-index-list";
import { GlobalSectorList } from "@/components/global-pulse/global-sector-list";
import { GlobalStockList } from "@/components/global-pulse/global-stock-list";
import { useGlobalIndices, useGlobalSectors, useGlobalStocks } from "@/hooks/use-global-pulse";
import { formatTimestamp } from "@/lib/utils";
import Link from "next/link";

const BASE_OPTIONS = ["NIFTY50", "NIFTY500"];
const PERIOD_OPTIONS = ["1W", "1M", "3M", "6M", "12M"];

export default function GlobalPulsePage() {
  const [base, setBase] = useState("NIFTY50");
  const [period, setPeriod] = useState("3M");
  const [selectedIndex, setSelectedIndex] = useState<string | null>(null);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  const { data: indicesData, isLoading: indicesLoading } = useGlobalIndices(base);
  const { data: sectorsData, isLoading: sectorsLoading } = useGlobalSectors(selectedIndex, base);
  const { data: stocksData, isLoading: stocksLoading } = useGlobalStocks(selectedSector);

  const handleSelectIndex = useCallback((key: string) => {
    setSelectedIndex(key);
    setSelectedSector(null);
  }, []);

  const handleSelectSector = useCallback((key: string) => {
    setSelectedSector(key);
  }, []);

  const handleResetToIndices = useCallback(() => {
    setSelectedIndex(null);
    setSelectedSector(null);
  }, []);

  const handleResetToSectors = useCallback(() => {
    setSelectedSector(null);
  }, []);

  // Build breadcrumb items
  const breadcrumbItems = [
    { label: "Global Markets", onClick: selectedIndex ? handleResetToIndices : undefined },
    ...(selectedIndex && indicesData
      ? [{ label: indicesData.indices.find((i) => i.key === selectedIndex)?.name || selectedIndex, onClick: selectedSector ? handleResetToSectors : undefined }]
      : []),
    ...(selectedSector && sectorsData
      ? [{ label: sectorsData.sectors.find((s) => s.key === selectedSector)?.name || selectedSector }]
      : []),
  ];

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Globe className="size-5 sm:size-6 text-teal-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Global Relative Strength</h1>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Drill down: Global Index → Sector → Stock — all benchmarked vs NIFTY
        </p>
        <Link href="/pulse" className="text-xs text-teal-600 hover:underline mt-1 inline-block">
          ← Back to Market Pulse
        </Link>
      </div>

      <PageInfo>
        Hierarchical relative strength analysis across global markets. Click an index to see its
        sector breakdown, then click a sector to see top stocks. Ratio returns show relative
        outperformance — positive means the instrument outperformed its benchmark over the period.
      </PageInfo>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <Select value={base} onValueChange={setBase}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Base" />
          </SelectTrigger>
          <SelectContent>
            {BASE_OPTIONS.map((opt) => (
              <SelectItem key={opt} value={opt}>{opt.replace("NIFTY", "NIFTY ")}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-[90px]">
            <SelectValue placeholder="Period" />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map((opt) => (
              <SelectItem key={opt} value={opt}>{opt}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {indicesData && (
          <p className="text-xs text-muted-foreground">
            {indicesData.count} indices • Last refreshed {formatTimestamp(indicesData.timestamp)}
          </p>
        )}
      </div>

      {/* Breadcrumb */}
      <GlobalBreadcrumb items={breadcrumbItems} />

      {/* Loading state */}
      {indicesLoading && (
        <div className="space-y-4">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-[400px] rounded-xl" />
        </div>
      )}

      {/* Content */}
      {!indicesLoading && indicesData && (
        <>
          {/* Heatmap — always visible */}
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <GlobalHeatmap
              indices={indicesData.indices}
              period={period}
              onSelect={handleSelectIndex}
            />
          </div>

          {/* 3-panel drill-down */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Panel 1: Global Indices */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 max-h-[600px] overflow-y-auto">
              <GlobalIndexList
                indices={indicesData.indices}
                period={period}
                selectedIndex={selectedIndex}
                onSelectIndex={handleSelectIndex}
              />
            </div>

            {/* Panel 2: Sectors */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 max-h-[600px] overflow-y-auto">
              {selectedIndex ? (
                <GlobalSectorList
                  sectors={sectorsData?.sectors ?? []}
                  marketName={indicesData.indices.find((i) => i.key === selectedIndex)?.name ?? selectedIndex}
                  period={period}
                  selectedSector={selectedSector}
                  onSelectSector={handleSelectSector}
                  isLoading={sectorsLoading}
                />
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <p className="text-sm text-muted-foreground">Select an index to see sector breakdown</p>
                </div>
              )}
            </div>

            {/* Panel 3: Stocks */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 max-h-[600px] overflow-y-auto">
              {selectedSector ? (
                <GlobalStockList
                  stocks={stocksData?.stocks ?? []}
                  sectorName={stocksData?.sector_name ?? selectedSector}
                  parentName={stocksData?.parent_name ?? ""}
                  period={period}
                  isLoading={stocksLoading}
                />
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <p className="text-sm text-muted-foreground">
                    {selectedIndex ? "Select a sector to see top stocks" : "Select an index first"}
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
