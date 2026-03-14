"use client";

import { useMemo, useState } from "react";
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
import { BASE_INDEX_OPTIONS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Zap, Loader2 } from "lucide-react";
import { SectorGroupSection } from "./sector-group-section";
import type { SectorInfo } from "@/app/recommendations/page";

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

const CATEGORY_LABELS: Record<string, string> = {
  sectoral: "Sectoral Indices",
  thematic: "Thematic Indices",
};

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
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const grouped = useMemo(() => {
    const groups: Record<string, SectorInfo[]> = {};
    for (const s of sectors) {
      const cat = s.category || "other";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(s);
    }
    const order = ["sectoral", "thematic"];
    const result: { category: string; label: string; items: SectorInfo[] }[] = [];
    for (const cat of order) {
      if (groups[cat]) {
        result.push({ category: cat, label: CATEGORY_LABELS[cat] || cat, items: groups[cat] });
      }
    }
    for (const cat of Object.keys(groups)) {
      if (!order.includes(cat)) {
        result.push({ category: cat, label: CATEGORY_LABELS[cat] || cat, items: groups[cat] });
      }
    }
    return result;
  }, [sectors]);

  function toggleSector(key: string) {
    if (selectedSectors.includes(key)) {
      onSelectedChange(selectedSectors.filter((k) => k !== key));
    } else {
      onSelectedChange([...selectedSectors, key]);
    }
  }

  function toggleAll() {
    onSelectedChange(selectedSectors.length === allKeys.length ? [] : [...allKeys]);
  }

  function selectAllInGroup(groupKeys: string[]) {
    onSelectedChange([...new Set([...selectedSectors, ...groupKeys])]);
  }

  function deselectAllInGroup(groupKeys: string[]) {
    const removeSet = new Set(groupKeys);
    onSelectedChange(selectedSectors.filter((k) => !removeSet.has(k)));
  }

  function toggleCollapse(cat: string) {
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));
  }

  const allSelected = selectedSectors.length === allKeys.length;
  const someSelected = selectedSectors.length > 0 && !allSelected;

  // Compute start index for each group (running numbering across groups)
  const groupStartIndices = useMemo(() => {
    const indices: number[] = [];
    let total = 0;
    for (const g of grouped) {
      indices.push(total);
      total += g.items.length;
    }
    return indices;
  }, [grouped]);

  return (
    <div className="border rounded-lg bg-white">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 border-b bg-gray-50/50">
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

        <Button onClick={onGenerate} disabled={loading || selectedSectors.length === 0} size="sm">
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

      {/* Global select all / threshold */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-3">
          <Checkbox
            checked={allSelected ? true : someSelected ? "indeterminate" : false}
            onCheckedChange={toggleAll}
          />
          <span className="text-xs font-medium text-muted-foreground">
            {selectedSectors.length} of {allKeys.length} selected
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-muted-foreground">Threshold:</span>
          <Input
            type="number"
            value={threshold}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              if (!isNaN(val)) onThresholdChange(val);
            }}
            className="w-16 h-7 text-xs text-center font-mono"
            step={0.5}
            min={0}
          />
          <span className="text-xs text-muted-foreground">%</span>
        </div>
      </div>

      {/* Grouped Sector Tables */}
      <div className="overflow-x-auto">
        {grouped.map((group, groupIdx) => (
          <SectorGroupSection
            key={group.category}
            category={group.category}
            label={group.label}
            items={group.items}
            isCollapsed={collapsed[group.category] ?? false}
            selectedSectors={selectedSectors}
            startIndex={groupStartIndices[groupIdx]}
            onToggleCollapse={() => toggleCollapse(group.category)}
            onSelectAllInGroup={selectAllInGroup}
            onDeselectAllInGroup={deselectAllInGroup}
            onToggleSector={toggleSector}
          />
        ))}
      </div>

      <p className="text-[10px] text-muted-foreground px-3 py-2 border-t">
        Select sectors and set a ratio return threshold (%). Sectors outperforming {base} by more than the threshold will show their top {topN} stocks.
      </p>
    </div>
  );
}
