"use client";

import { useState, useEffect } from "react";
import { Compass } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ThresholdGrid } from "@/components/recommendations/threshold-grid";
import { RecommendationResults } from "@/components/recommendations/recommendation-results";

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
  results: Record<string, { qualifying_sectors: Array<Record<string, unknown>> }>;
  generated_at: string;
}

export default function RecommendationsPage() {
  const [sectors, setSectors] = useState<SectorInfo[]>([]);
  const [periods, setPeriods] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState("");

  // Load sector list on mount
  useEffect(() => {
    async function loadSectors() {
      try {
        const res = await fetch(`${API}/api/recommendations/sectors`);
        if (!res.ok) throw new Error("Failed to load sectors");
        const data: SectorsResponse = await res.json();
        setSectors(data.sectors);
        setPeriods(data.periods);
      } catch (err) {
        setError("Failed to load sector data. Is the backend running?");
      } finally {
        setLoading(false);
      }
    }
    loadSectors();
  }, []);

  async function handleGenerate(base: string, thresholds: Record<string, Record<string, number>>) {
    setGenerating(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/recommendations/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ base, thresholds }),
      });
      if (!res.ok) throw new Error("Generation failed");
      const data: GenerateResponse = await res.json();
      setResults(data);
    } catch {
      setError("Failed to generate recommendations. Please try again.");
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
          Set ratio return thresholds per sector — outperforming sectors surface their top stocks and ETFs
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

      {/* Threshold Grid */}
      {!loading && sectors.length > 0 && (
        <ThresholdGrid
          sectors={sectors}
          periods={periods}
          onGenerate={handleGenerate}
          loading={generating}
        />
      )}

      {/* Results */}
      {results && results.results && (
        <>
          <hr className="border-border" />
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <RecommendationResults results={results.results as any} base={results.base} />
          <p className="text-[10px] text-muted-foreground text-right">
            Generated at {new Date(results.generated_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
          </p>
        </>
      )}
    </div>
  );
}
