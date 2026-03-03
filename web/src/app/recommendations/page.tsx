"use client";

import { useState, useEffect } from "react";
import { Compass } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { SectorSelectionPanel } from "@/components/recommendations/sector-selection-panel";
import { RecommendationResults } from "@/components/recommendations/recommendation-results";
import type { SectorResult } from "@/components/recommendations/sector-result-card";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface SectorInfo {
  key: string;
  display_name: string;
  etfs: string[];
}

interface SectorsResponse {
  success: boolean;
  sectors: SectorInfo[];
  periods: string[];
}

interface GenerateResponse {
  success: boolean;
  base: string;
  period: string;
  threshold: number;
  qualifying_sectors: SectorResult[];
  non_qualifying_sectors: SectorResult[];
  generated_at: string;
}

export default function RecommendationsPage() {
  const [sectors, setSectors] = useState<SectorInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState("");

  // Selection state
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [base, setBase] = useState("NIFTY");
  const [period, setPeriod] = useState("1m");
  const [threshold, setThreshold] = useState(5);

  // Load sector list on mount
  useEffect(() => {
    async function loadSectors() {
      try {
        const res = await fetch(`${API}/api/recommendations/sectors`);
        if (!res.ok) throw new Error("Failed to load sectors");
        const data: SectorsResponse = await res.json();
        setSectors(data.sectors);
        // Select all sectors by default
        setSelectedSectors(data.sectors.map((s) => s.key));
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(`Failed to load sector data: ${message}. Is the backend running?`);
      } finally {
        setLoading(false);
      }
    }
    loadSectors();
  }, []);

  async function handleGenerate() {
    if (selectedSectors.length === 0) {
      setError("Select at least one sector");
      return;
    }
    setGenerating(true);
    setError("");
    setResults(null);
    try {
      const res = await fetch(`${API}/api/recommendations/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base,
          period,
          selected_sectors: selectedSectors,
          threshold,
        }),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        const detail = errorData?.detail || `HTTP ${res.status}`;
        throw new Error(`Generation failed: ${detail}`);
      }
      const data: GenerateResponse = await res.json();
      setResults(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("Generate recommendations failed:", err);
      setError(message);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Compass className="size-5 sm:size-6 text-teal-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Sector Recommendations</h1>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Select sectors and set a threshold — outperforming sectors surface their top stocks and ETFs with fundamentals
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-12 rounded-lg" />
          <Skeleton className="h-[400px] rounded-lg" />
        </div>
      )}

      {/* Sector Selection Panel */}
      {!loading && sectors.length > 0 && (
        <SectorSelectionPanel
          sectors={sectors}
          selectedSectors={selectedSectors}
          onSelectedChange={setSelectedSectors}
          base={base}
          onBaseChange={setBase}
          period={period}
          onPeriodChange={setPeriod}
          threshold={threshold}
          onThresholdChange={setThreshold}
          onGenerate={handleGenerate}
          loading={generating}
        />
      )}

      {/* Results */}
      {results && (
        <>
          <hr className="border-border" />
          <RecommendationResults
            qualifyingSectors={results.qualifying_sectors}
            nonQualifyingSectors={results.non_qualifying_sectors}
            base={results.base}
            period={results.period}
            threshold={results.threshold}
          />
          <p className="text-[10px] text-muted-foreground text-right">
            Generated at {new Date(results.generated_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
          </p>
        </>
      )}
    </div>
  );
}
