"use client";

import type { SectorRS, CompassAction } from "@/lib/compass-types";

const ACTION_STYLES: Record<CompassAction, { bg: string; text: string }> = {
  BUY: { bg: "bg-emerald-100", text: "text-emerald-700" },
  ACCUMULATE: { bg: "bg-teal-100", text: "text-teal-700" },
  WATCH: { bg: "bg-blue-100", text: "text-blue-700" },
  HOLD: { bg: "bg-amber-100", text: "text-amber-700" },
  SELL: { bg: "bg-red-100", text: "text-red-700" },
  AVOID: { bg: "bg-slate-100", text: "text-slate-600" },
  EXIT: { bg: "bg-red-200", text: "text-red-800" },
};

interface Props {
  sectors: SectorRS[];
}

export function ActionSummary({ sectors }: Props) {
  const grouped: Record<string, SectorRS[]> = {};
  for (const s of sectors) {
    if (!grouped[s.action]) grouped[s.action] = [];
    grouped[s.action].push(s);
  }

  const actionOrder: CompassAction[] = ["BUY", "ACCUMULATE", "WATCH", "HOLD", "SELL", "AVOID"];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <h3 className="text-sm font-semibold text-slate-900 mb-3">Action Summary</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {actionOrder.map((action) => {
          const items = grouped[action] || [];
          const style = ACTION_STYLES[action];
          return (
            <div key={action} className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className={`${style.bg} ${style.text} rounded-full px-2.5 py-0.5 text-xs font-semibold`}>
                  {action}
                </span>
                <span className="text-xs text-slate-400">{items.length}</span>
              </div>
              {items.map((s) => (
                <p key={s.sector_key} className="text-xs text-slate-600 pl-1 truncate" title={s.display_name}>
                  {s.display_name}
                  {s.etfs.length > 0 && (
                    <span className="text-slate-400 ml-1">({s.etfs[0]})</span>
                  )}
                </p>
              ))}
              {items.length === 0 && (
                <p className="text-xs text-slate-300 pl-1">None</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
