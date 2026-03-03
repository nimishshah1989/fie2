"use client";

import { useState, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BASE_INDEX_OPTIONS } from "@/lib/constants";
import { Zap } from "lucide-react";

interface SectorInfo {
  key: string;
  display_name: string;
  etfs: string[];
}

interface ThresholdGridProps {
  sectors: SectorInfo[];
  periods: string[];
  onGenerate: (base: string, thresholds: Record<string, Record<string, number>>) => void;
  loading: boolean;
}

const PERIOD_LABELS: Record<string, string> = {
  "1w": "1W",
  "1m": "1M",
  "3m": "3M",
  "6m": "6M",
  "12m": "12M",
};

const DEFAULT_THRESHOLDS: Record<string, number> = {
  "1w": 2,
  "1m": 5,
  "3m": 10,
  "6m": 15,
  "12m": 20,
};

export function ThresholdGrid({ sectors, periods, onGenerate, loading }: ThresholdGridProps) {
  const [base, setBase] = useState("NIFTY");

  // Grid state: { sectorKey: { period: value } }
  const [grid, setGrid] = useState<Record<string, Record<string, string>>>(() => {
    const initial: Record<string, Record<string, string>> = {};
    for (const s of sectors) {
      initial[s.key] = {};
      for (const p of periods) {
        initial[s.key][p] = String(DEFAULT_THRESHOLDS[p] ?? "");
      }
    }
    return initial;
  });

  // "Apply to All" values per column
  const [applyAllValues, setApplyAllValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const p of periods) {
      init[p] = String(DEFAULT_THRESHOLDS[p] ?? "");
    }
    return init;
  });

  const updateCell = useCallback((sectorKey: string, period: string, value: string) => {
    setGrid((prev) => ({
      ...prev,
      [sectorKey]: {
        ...prev[sectorKey],
        [period]: value,
      },
    }));
  }, []);

  function applyToAll(period: string) {
    const val = applyAllValues[period];
    setGrid((prev) => {
      const next = { ...prev };
      for (const s of sectors) {
        next[s.key] = { ...next[s.key], [period]: val };
      }
      return next;
    });
  }

  function handleGenerate() {
    const thresholds: Record<string, Record<string, number>> = {};
    for (const s of sectors) {
      thresholds[s.key] = {};
      for (const p of periods) {
        const val = parseFloat(grid[s.key]?.[p] ?? "");
        if (!isNaN(val)) {
          thresholds[s.key][p] = val;
        }
      }
    }
    onGenerate(base, thresholds);
  }

  return (
    <div className="space-y-4">
      {/* Base selector + Generate button */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Base:</span>
          <Select value={base} onValueChange={setBase}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {BASE_INDEX_OPTIONS.map((opt) => (
                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1" />
        <Button onClick={handleGenerate} disabled={loading}>
          <Zap className="h-4 w-4 mr-1.5" />
          {loading ? "Generating..." : "Generate Recommendations"}
        </Button>
      </div>

      {/* Threshold Grid */}
      <div className="border rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50 border-b">
              <th className="text-left py-2 px-3 text-xs font-semibold text-muted-foreground w-[200px]">
                Sector Index
              </th>
              {periods.map((p) => (
                <th key={p} className="text-center py-2 px-2 text-xs font-semibold text-muted-foreground w-[80px]">
                  {PERIOD_LABELS[p] || p}
                </th>
              ))}
            </tr>
            {/* Apply to All row */}
            <tr className="bg-muted/30 border-b">
              <td className="py-1.5 px-3 text-[10px] font-semibold text-muted-foreground uppercase">
                Apply to All
              </td>
              {periods.map((p) => (
                <td key={p} className="py-1.5 px-1 text-center">
                  <div className="flex items-center gap-1 justify-center">
                    <Input
                      type="number"
                      value={applyAllValues[p] ?? ""}
                      onChange={(e) => setApplyAllValues((prev) => ({ ...prev, [p]: e.target.value }))}
                      className="w-14 h-7 text-xs text-center font-mono p-1"
                      step={0.5}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => applyToAll(p)}
                      className="h-7 px-1.5 text-[10px]"
                      title={`Apply ${applyAllValues[p]}% to all sectors for ${PERIOD_LABELS[p]}`}
                    >
                      All
                    </Button>
                  </div>
                </td>
              ))}
            </tr>
          </thead>
          <tbody>
            {sectors.map((sector, idx) => (
              <tr
                key={sector.key}
                className={idx % 2 === 0 ? "" : "bg-muted/20"}
              >
                <td className="py-1.5 px-3">
                  <div className="text-xs font-medium">{sector.display_name}</div>
                  {sector.etfs.length > 0 && (
                    <div className="text-[10px] text-muted-foreground">
                      ETF: {sector.etfs.join(", ")}
                    </div>
                  )}
                </td>
                {periods.map((p) => (
                  <td key={p} className="py-1.5 px-1 text-center">
                    <Input
                      type="number"
                      value={grid[sector.key]?.[p] ?? ""}
                      onChange={(e) => updateCell(sector.key, p, e.target.value)}
                      className="w-14 h-7 text-xs text-center font-mono p-1 mx-auto"
                      step={0.5}
                      placeholder="%"
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-muted-foreground">
        Enter ratio return thresholds (%) for each sector. Sectors that outperform the base by more than the threshold will appear in results.
      </p>
    </div>
  );
}
