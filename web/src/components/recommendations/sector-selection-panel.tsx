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
import { BASE_INDEX_OPTIONS, SECTOR_COLORS, SECTOR_GROUPS } from "@/lib/constants";
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

// Build a lookup from key → SectorInfo for quick access
function buildSectorMap(sectors: SectorInfo[]): Record<string, SectorInfo> {
  const map: Record<string, SectorInfo> = {};
  for (const s of sectors) {
    map[s.key] = s;
  }
  return map;
}

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
  onGenerate,
  loading,
}: SectorSelectionPanelProps) {
  const sectorMap = buildSectorMap(sectors);
  const allKeys = sectors.map((s) => s.key);

  function toggleSector(key: string) {
    if (selectedSectors.includes(key)) {
      onSelectedChange(selectedSectors.filter((k) => k !== key));
    } else {
      onSelectedChange([...selectedSectors, key]);
    }
  }

  function selectAll() {
    onSelectedChange([...allKeys]);
  }

  function clearAll() {
    onSelectedChange([]);
  }

  function toggleGroup(groupSectors: string[]) {
    const allSelected = groupSectors.every((k) => selectedSectors.includes(k));
    if (allSelected) {
      onSelectedChange(selectedSectors.filter((k) => !groupSectors.includes(k)));
    } else {
      const newSet = new Set([...selectedSectors, ...groupSectors]);
      onSelectedChange([...newSet]);
    }
  }

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

        {/* Threshold */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Threshold:</span>
          <Input
            type="number"
            value={threshold}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              if (!isNaN(val)) onThresholdChange(val);
            }}
            className="w-16 h-8 text-xs text-center font-mono"
            step={0.5}
            min={0}
          />
          <span className="text-xs text-muted-foreground">%</span>
        </div>

        <div className="flex-1" />

        {/* Select All / Clear */}
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={selectAll} className="h-7 px-2 text-[10px]">
            Select All
          </Button>
          <Button variant="ghost" size="sm" onClick={clearAll} className="h-7 px-2 text-[10px]">
            Clear
          </Button>
        </div>
      </div>

      {/* Sector Groups */}
      <div className="p-3 space-y-1">
        {SECTOR_GROUPS.map((group) => {
          const groupSectorKeys = group.sectors.filter((k) => k in sectorMap);
          if (groupSectorKeys.length === 0) return null;
          const allGroupSelected = groupSectorKeys.every((k) => selectedSectors.includes(k));
          const someGroupSelected = groupSectorKeys.some((k) => selectedSectors.includes(k));

          return (
            <div key={group.label} className="space-y-0">
              {/* Group header (clickable to toggle all in group) */}
              <button
                onClick={() => toggleGroup(groupSectorKeys)}
                className="flex items-center gap-2 py-1.5 px-2 w-full text-left hover:bg-gray-50 rounded transition-colors"
              >
                <Checkbox
                  checked={allGroupSelected ? true : someGroupSelected ? "indeterminate" : false}
                  className="pointer-events-none"
                />
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {group.label}
                </span>
              </button>

              {/* Individual sectors */}
              {groupSectorKeys.map((key) => {
                const info = sectorMap[key];
                if (!info) return null;
                const colors = SECTOR_COLORS[key];
                const isSelected = selectedSectors.includes(key);

                return (
                  <button
                    key={key}
                    onClick={() => toggleSector(key)}
                    className={cn(
                      "flex items-center gap-3 py-1.5 px-2 pl-8 w-full text-left rounded transition-colors border-l-3",
                      isSelected && colors ? `${colors.bg} ${colors.border}` : "border-transparent hover:bg-gray-50"
                    )}
                  >
                    <Checkbox
                      checked={isSelected}
                      className="pointer-events-none"
                    />
                    <span className={cn(
                      "text-xs font-medium flex-1",
                      isSelected && colors ? colors.text : "text-foreground"
                    )}>
                      {info.display_name}
                    </span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {key}
                    </span>
                    {info.etfs.length > 0 && (
                      <span className="text-[10px] text-muted-foreground">
                        ETF: {info.etfs.join(", ")}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Generate Button */}
      <div className="p-3 border-t bg-gray-50/50">
        <Button
          onClick={onGenerate}
          disabled={loading || selectedSectors.length === 0}
          className="w-full"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Zap className="h-4 w-4 mr-1.5" />
              Generate Recommendations ({selectedSectors.length} sector{selectedSectors.length !== 1 ? "s" : ""})
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
