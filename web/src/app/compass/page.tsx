"use client";

import { useState, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompassSectors, useCompassStocks } from "@/hooks/use-compass";
import { SectorBubbleChart } from "@/components/compass/SectorBubbleChart";
import { ActionSummary } from "@/components/compass/ActionSummary";
import { StockDrillDown } from "@/components/compass/StockDrillDown";
import { ETFView } from "@/components/compass/ETFView";
import { ModelPortfolioDashboard } from "@/components/compass/ModelPortfolioDashboard";
import { CompassMethodology } from "@/components/compass/CompassMethodology";
import { refreshCompass } from "@/lib/compass-api";
import type { Period } from "@/lib/compass-types";

const PERIODS: Period[] = ["1M", "3M", "6M", "12M"];
const BASES = ["NIFTY", "NIFTY100", "NIFTY500"];
const TABS = ["Sectors", "ETFs", "Model Portfolio", "Methodology"] as const;

export default function CompassPage() {
  const [base, setBase] = useState("NIFTY");
  const [period, setPeriod] = useState<Period>("3M");
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("Sectors");
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const { sectors, isLoading: loadingSectors, mutate: mutateSectors } = useCompassSectors(base, period);
  const { stocks, isLoading: loadingStocks } = useCompassStocks(selectedSector, base, period);

  const selectedSectorInfo = sectors.find((s) => s.sector_key === selectedSector);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshCompass();
      mutateSectors();
    } catch {
      // silent
    } finally {
      setRefreshing(false);
    }
  }, [mutateSectors]);

  const handleSectorClick = useCallback((sectorKey: string) => {
    setSelectedSector(sectorKey);
    // If clicking from action board, switch to Sectors tab
    if (activeTab !== "Sectors") setActiveTab("Sectors");
  }, [activeTab]);

  // Show base/period controls for Sectors and ETFs tabs
  const showControls = (activeTab === "Sectors" && !selectedSector) || activeTab === "ETFs";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Sector Compass</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Relative strength, momentum & value — click any sector to drill into stocks
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Computing..." : "Refresh RS"}
        </Button>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab);
              setSelectedSector(null);
            }}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Base & Period controls — shared between Sectors and ETFs */}
      {showControls && (
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Base</span>
            <div className="flex gap-1">
              {BASES.map((b) => (
                <button
                  key={b}
                  onClick={() => setBase(b)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    base === b
                      ? "bg-teal-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {b}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Period</span>
            <div className="flex gap-1">
              {PERIODS.map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    period === p
                      ? "bg-teal-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <span className="text-xs text-slate-400 ml-auto">
            {sectors.length} sectors tracked
            {sectors[0]?.last_updated && (
              <span className="ml-2 text-slate-300">
                Updated: {sectors[0].last_updated}
              </span>
            )}
          </span>
        </div>
      )}

      {/* Sectors tab */}
      {activeTab === "Sectors" && (
        <>
          {loadingSectors ? (
            <div className="space-y-4">
              <Skeleton className="h-[480px] w-full rounded-xl" />
              <Skeleton className="h-24 w-full rounded-xl" />
            </div>
          ) : selectedSector && selectedSectorInfo ? (
            <StockDrillDown
              sectorInfo={selectedSectorInfo}
              stocks={stocks}
              loadingStocks={loadingStocks}
              onBack={() => setSelectedSector(null)}
            />
          ) : (
            <>
              <SectorBubbleChart
                sectors={sectors}
                onSectorClick={handleSectorClick}
              />
              <ActionSummary sectors={sectors} onSectorClick={handleSectorClick} />
            </>
          )}
        </>
      )}

      {/* ETFs tab */}
      {activeTab === "ETFs" && <ETFView base={base} period={period} />}

      {/* Model Portfolio tab */}
      {activeTab === "Model Portfolio" && <ModelPortfolioDashboard />}

      {/* Methodology tab */}
      {activeTab === "Methodology" && <CompassMethodology />}
    </div>
  );
}
