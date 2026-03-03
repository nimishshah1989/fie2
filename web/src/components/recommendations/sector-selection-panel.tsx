"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BASE_INDEX_OPTIONS, SECTOR_COLORS, SECTOR_CATEGORY } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Zap, Loader2 } from "lucide-react";

interface SectorInfo {
  key: string;
  display_name: string;
  etfs: string[];
}

interface SectorSelectionPanelProps {
  sectors: SectorInfo[];
  selectedSectors: string[];
  onSelectedChange: (selected: string[]) => void;
  base: string;
  onBaseChange: (base: string) => void;
  period: string;
  onPeriodChange: (period: string) => void;
  threshold: number;
  onThresholdChange: (threshold: number) => void;
  topN: number;
  onTopNChange: (n: number) => void;
  onGenerate: () => void;
  loading: boolean;
}

const PERIOD_TABS = [
  { key: "1w", label: "1W" },
  { key: "1m", label: "1M" },
  { key: "3m", label: "3M" },
  { key: "6m", label: "6M" },
  { key: "12m", label: "12M" },
];

export function SectorSelectionPanel({
  sectors,
  selectedSectors,
  onSelectedChange,
  base,
  onBaseChange,
  period,
  onPeriodChange,
  threshold,
  onThresholdChange,
  topN,
  onTopNChange,
  onGenerate,
  loading,
}: SectorSelectionPanelProps) {
  const allKeys = sectors.map((s) => s.key);

  function toggleSector(key: string) {
    if (selectedSectors.includes(key)) {
      onSelectedChange(selectedSectors.filter((k) => k !== key));
    } else {
      onSelectedChange([...selectedSectors, key]);
    }
  }

  function toggleAll() {
    if (selectedSectors.length === allKeys.length) {
      onSelectedChange([]);
    } else {
      onSelectedChange([...allKeys]);
    }
  }

  const allSelected = selectedSectors.length === allKeys.length;
  const someSelected = selectedSectors.length > 0 && !allSelected;

  return (
    <div className="border rounded-lg bg-white">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 border-b bg-gray-50/50">
        {/* Base Selector */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Base:</span>
          <Select value={base} onValueChange={onBaseChange}>
            <SelectTrigger className="w-[120px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {BASE_INDEX_OPTIONS.map((opt) => (
                <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Period Tabs */}
        <div className="flex items-center gap-0.5 bg-muted rounded-md p-0.5">
          {PERIOD_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => onPeriodChange(tab.key)}
              className={cn(
                "px-2.5 py-1 text-xs font-medium rounded transition-colors",
                period === tab.key
                  ? "bg-white text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Top N stocks */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Top</span>
          <Input
            type="number"
            value={topN}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              if (!isNaN(val) && val >= 1 && val <= 10) onTopNChange(val);
            }}
            className="w-14 h-8 text-xs text-center font-mono"
            min={1}
            max={10}
          />
          <span className="text-xs font-medium text-muted-foreground">stocks</span>
        </div>

        <div className="flex-1" />

        {/* Generate Button */}
        <Button
          onClick={onGenerate}
          disabled={loading || selectedSectors.length === 0}
          size="sm"
        >
          {loading ? (
            <>
              <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Zap className="h-3.5 w-3.5 mr-1.5" />
              Generate ({selectedSectors.length})
            </>
          )}
        </Button>
      </div>

      {/* Sector Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/40 border-b">
              <th className="py-2 px-3 text-left w-10">
                <Checkbox
                  checked={allSelected ? true : someSelected ? "indeterminate" : false}
                  onCheckedChange={toggleAll}
                />
              </th>
              <th className="py-2 px-2 text-left text-[10px] font-semibold text-muted-foreground uppercase w-8">#</th>
              <th className="py-2 px-2 text-left text-[10px] font-semibold text-muted-foreground uppercase">Index</th>
              <th className="py-2 px-2 text-left text-[10px] font-semibold text-muted-foreground uppercase">Sector</th>
              <th className="py-2 px-2 text-left text-[10px] font-semibold text-muted-foreground uppercase">ETF</th>
              <th className="py-2 px-2 text-center text-[10px] font-semibold text-muted-foreground uppercase w-[100px]">
                <div className="flex flex-col items-center gap-0.5">
                  <span>Threshold %</span>
                  <button
                    onClick={() => {
                      // Apply current threshold to all is implicit — single threshold
                    }}
                    className="text-[9px] text-teal-600 hover:underline font-normal normal-case"
                  >
                    (applies to all)
                  </button>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {sectors.map((sector, idx) => {
              const isSelected = selectedSectors.includes(sector.key);
              const colors = SECTOR_COLORS[sector.key];
              const category = SECTOR_CATEGORY[sector.key] || "—";

              return (
                <tr
                  key={sector.key}
                  onClick={() => toggleSector(sector.key)}
                  className={cn(
                    "cursor-pointer transition-colors border-b border-border/50",
                    isSelected && colors ? colors.bg : idx % 2 === 0 ? "" : "bg-muted/20",
                    "hover:bg-muted/30"
                  )}
                >
                  <td className="py-1.5 px-3" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => toggleSector(sector.key)}
                    />
                  </td>
                  <td className="py-1.5 px-2 text-xs text-muted-foreground">{idx + 1}</td>
                  <td className="py-1.5 px-2">
                    <div className="flex items-center gap-2">
                      {colors && (
                        <div className={cn("w-1 h-4 rounded-full", colors.border.replace("border-", "bg-"))} />
                      )}
                      <span className={cn("text-xs font-medium", isSelected && colors ? colors.text : "text-foreground")}>
                        {sector.display_name}
                      </span>
                    </div>
                  </td>
                  <td className="py-1.5 px-2 text-xs text-muted-foreground">{category}</td>
                  <td className="py-1.5 px-2 text-xs font-mono text-muted-foreground">
                    {sector.etfs.length > 0 ? sector.etfs.join(", ") : "—"}
                  </td>
                  <td className="py-1.5 px-2 text-center" onClick={(e) => e.stopPropagation()}>
                    <Input
                      type="number"
                      value={threshold}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value);
                        if (!isNaN(val)) onThresholdChange(val);
                      }}
                      className="w-16 h-7 text-xs text-center font-mono mx-auto"
                      step={0.5}
                      min={0}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-muted-foreground px-3 py-2 border-t">
        Select sectors and set a ratio return threshold (%). Sectors outperforming {base} by more than the threshold will show their top {topN} stocks.
      </p>
    </div>
  );
}
