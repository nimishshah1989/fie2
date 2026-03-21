"use client";

import { ArrowUpRight } from "lucide-react";
import type { SectorRS, CompassAction } from "@/lib/compass-types";

const ACTION_CONFIG: Record<CompassAction, {
  bg: string; text: string; border: string;
  label: string; description: string;
}> = {
  BUY: {
    bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200",
    label: "BUY", description: "Strong momentum + smart money accumulating. Enter via ETF or top stocks.",
  },
  ACCUMULATE: {
    bg: "bg-teal-50", text: "text-teal-700", border: "border-teal-200",
    label: "ACCUMULATE", description: "Improving strength. Add on dips or build position gradually.",
  },
  WATCH: {
    bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200",
    label: "WATCH", description: "Gaining momentum but volume not confirming yet. Wait for confirmation.",
  },
  HOLD: {
    bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200",
    label: "HOLD", description: "Still strong but momentum fading. Tighten stops, no new entries.",
  },
  SELL: {
    bg: "bg-red-50", text: "text-red-700", border: "border-red-200",
    label: "SELL", description: "Distribution confirmed. Exit positions. Book profits or cut losses.",
  },
  AVOID: {
    bg: "bg-slate-50", text: "text-slate-600", border: "border-slate-200",
    label: "AVOID", description: "Weak and getting weaker. No reason to be here. Wait for reversal.",
  },
  EXIT: {
    bg: "bg-red-100", text: "text-red-800", border: "border-red-300",
    label: "EXIT", description: "Immediate exit. Stop-loss or trailing stop triggered.",
  },
};

interface Props {
  sectors: SectorRS[];
  onSectorClick?: (sectorKey: string) => void;
}

export function ActionSummary({ sectors, onSectorClick }: Props) {
  const grouped: Record<string, SectorRS[]> = {};
  for (const s of sectors) {
    if (!grouped[s.action]) grouped[s.action] = [];
    grouped[s.action].push(s);
  }

  // Only show actions that have sectors, in priority order
  const actionOrder: CompassAction[] = ["BUY", "ACCUMULATE", "SELL", "EXIT", "WATCH", "HOLD", "AVOID"];
  const activeActions = actionOrder.filter((a) => grouped[a]?.length);

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-900">Action Board</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {activeActions.map((action) => {
          const config = ACTION_CONFIG[action];
          const items = grouped[action] || [];
          return (
            <div
              key={action}
              className={`${config.bg} rounded-xl border ${config.border} p-4`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`${config.text} text-sm font-bold`}>{config.label}</span>
                  <span className={`${config.text} opacity-60 text-xs font-medium`}>
                    {items.length} sector{items.length !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
              <p className={`text-xs ${config.text} opacity-70 mb-3`}>{config.description}</p>
              <div className="space-y-1.5">
                {items
                  .sort((a, b) => b.rs_score - a.rs_score)
                  .map((s) => (
                    <button
                      key={s.sector_key}
                      onClick={() => onSectorClick?.(s.sector_key)}
                      className="w-full flex items-center justify-between bg-white/70 hover:bg-white rounded-lg px-3 py-2 transition-colors group text-left"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate">
                          {s.display_name}
                        </p>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-slate-500">
                            RS <span className="font-mono font-semibold">{s.rs_score.toFixed(1)}</span>
                          </span>
                          <span className={`text-xs font-mono font-semibold ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
                            {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum.toFixed(1)}
                          </span>
                          {s.volume_signal && (
                            <span className="text-xs text-slate-400">
                              {s.volume_signal.replace("_", " ")}
                            </span>
                          )}
                          {s.etfs.length > 0 && (
                            <span className="text-xs text-teal-600 font-medium">{s.etfs[0]}</span>
                          )}
                        </div>
                      </div>
                      <ArrowUpRight className="h-3.5 w-3.5 text-slate-300 group-hover:text-slate-500 shrink-0 ml-2" />
                    </button>
                  ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
