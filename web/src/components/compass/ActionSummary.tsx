"use client";

import { ArrowUpRight } from "lucide-react";
import type { SectorRS, CompassAction } from "@/lib/compass-types";
import { actionLabel, watchSubLabel, isWatch } from "@/lib/compass-types";

const ACTION_CONFIG: Record<CompassAction, {
  bg: string; text: string; border: string;
  label: string; description: string;
}> = {
  BUY: {
    bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200",
    label: "BUY", description: "Rising, outperforming benchmark, and gaining momentum. All 3 gates pass.",
  },
  HOLD: {
    bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200",
    label: "HOLD", description: "Outperforming but momentum fading, or BUY downgraded by volume/regime. Tighten stops, no new entry.",
  },
  WATCH_EMERGING: {
    bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200",
    label: "WATCH — Emerging", description: "Rising and strengthening but still lagging market. Watch for RS crossing above 0.",
  },
  WATCH_RELATIVE: {
    bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200",
    label: "WATCH — Relative", description: "Outperforming and strengthening vs market, but price still falling. Watch for absolute return turning positive.",
  },
  WATCH_EARLY: {
    bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200",
    label: "WATCH — Early", description: "Momentum just turned positive — earliest reversal signal. Needs both RS and price to confirm.",
  },
  AVOID: {
    bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200",
    label: "AVOID", description: "Rising but underperforming with fading momentum. Poor risk/reward.",
  },
  SELL: {
    bg: "bg-red-50", text: "text-red-700", border: "border-red-200",
    label: "SELL", description: "Multiple gates failing. Underperforming and/or falling with no momentum support.",
  },
};

/** Display order for the action board */
const ACTION_ORDER: CompassAction[] = [
  "BUY", "SELL", "HOLD", "WATCH_EMERGING", "WATCH_RELATIVE", "WATCH_EARLY", "AVOID",
];

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

  const activeActions = ACTION_ORDER.filter((a) => grouped[a]?.length);

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
                        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
                          <span className="text-xs text-slate-500">
                            RS <span className={`font-mono font-semibold ${s.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>{s.rs_score > 0 ? "+" : ""}{s.rs_score.toFixed(1)}%</span>
                          </span>
                          {s.absolute_return != null && (
                            <span className={`text-xs font-mono ${s.absolute_return > 0 ? "text-emerald-600" : "text-red-600"}`}>
                              Abs {s.absolute_return > 0 ? "+" : ""}{s.absolute_return.toFixed(1)}%
                            </span>
                          )}
                          {s.pe_zone && (
                            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                              s.pe_zone === "VALUE" ? "bg-emerald-100 text-emerald-700" :
                              s.pe_zone === "FAIR" ? "bg-slate-100 text-slate-600" :
                              s.pe_zone === "STRETCHED" ? "bg-amber-100 text-amber-700" :
                              "bg-red-100 text-red-700"
                            }`}>
                              {s.pe_zone}{s.pe_ratio ? ` (${s.pe_ratio.toFixed(0)})` : ""}
                            </span>
                          )}
                          {s.volume_signal && (
                            <span className="text-xs text-slate-400">
                              {s.volume_signal.replace("_", " ")}
                            </span>
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
