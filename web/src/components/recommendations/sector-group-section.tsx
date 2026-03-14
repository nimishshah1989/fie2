"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { SECTOR_COLORS, SECTOR_CATEGORY } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { SectorInfo } from "@/app/recommendations/page";

interface SectorGroupSectionProps {
  category: string;
  label: string;
  items: SectorInfo[];
  isCollapsed: boolean;
  selectedSectors: string[];
  startIndex: number;
  onToggleCollapse: () => void;
  onSelectAllInGroup: (keys: string[]) => void;
  onDeselectAllInGroup: (keys: string[]) => void;
  onToggleSector: (key: string) => void;
}

export function SectorGroupSection({
  category,
  label,
  items,
  isCollapsed,
  selectedSectors,
  startIndex,
  onToggleCollapse,
  onSelectAllInGroup,
  onDeselectAllInGroup,
  onToggleSector,
}: SectorGroupSectionProps) {
  const groupKeys = items.map((s) => s.key);
  const groupSelected = groupKeys.filter((k) => selectedSectors.includes(k));
  const allGroupSelected = groupSelected.length === groupKeys.length;

  return (
    <div>
      {/* Category Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-t">
        <button
          onClick={onToggleCollapse}
          className="flex items-center gap-2 text-xs font-semibold text-slate-600 uppercase tracking-wider"
        >
          {isCollapsed ? (
            <ChevronRight className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
          {label} ({items.length})
        </button>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground">
            {groupSelected.length}/{groupKeys.length}
          </span>
          <button
            onClick={() => allGroupSelected ? onDeselectAllInGroup(groupKeys) : onSelectAllInGroup(groupKeys)}
            className="text-[10px] text-teal-600 hover:text-teal-700 font-medium"
          >
            {allGroupSelected ? "Deselect All" : "Select All"}
          </button>
        </div>
      </div>

      {/* Sector Rows */}
      {!isCollapsed && (
        <table className="w-full text-sm">
          <tbody>
            {items.map((sector, localIdx) => {
              const idx = startIndex + localIdx + 1;
              const isSelected = selectedSectors.includes(sector.key);
              const colors = SECTOR_COLORS[sector.key];
              const sectorCategory = SECTOR_CATEGORY[sector.key] || "";

              return (
                <tr
                  key={sector.key}
                  onClick={() => onToggleSector(sector.key)}
                  className={cn(
                    "cursor-pointer transition-colors border-b border-border/50",
                    isSelected && colors ? colors.bg : idx % 2 === 0 ? "" : "bg-muted/20",
                    "hover:bg-muted/30"
                  )}
                >
                  <td className="py-1.5 px-3 w-10" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={isSelected}
                      onCheckedChange={() => onToggleSector(sector.key)}
                    />
                  </td>
                  <td className="py-1.5 px-2 text-xs text-muted-foreground w-8">{idx}</td>
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
                  <td className="py-1.5 px-2 text-xs text-muted-foreground">{sectorCategory}</td>
                  <td className="py-1.5 px-2 text-xs font-mono text-muted-foreground">
                    {sector.etfs.length > 0 ? sector.etfs.join(", ") : ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
