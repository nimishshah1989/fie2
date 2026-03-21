"use client";

import { useState } from "react";
import { ArrowUpRight, LayoutGrid, Table2 } from "lucide-react";
import type { SectorRS, CompassAction } from "@/lib/compass-types";
import { actionLabel, volumeLabel, volumeDescription, peZoneLabel } from "@/lib/compass-types";

const ACTION_CONFIG: Record<CompassAction, {
  bg: string; text: string; border: string;
  pillBg: string; pillText: string;
  label: string; shortLabel: string;
}> = {
  BUY: {
    bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200",
    pillBg: "bg-emerald-600", pillText: "text-white",
    label: "BUY", shortLabel: "BUY",
  },
  HOLD: {
    bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200",
    pillBg: "bg-amber-500", pillText: "text-white",
    label: "HOLD", shortLabel: "HOLD",
  },
  WATCH_EMERGING: {
    bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200",
    pillBg: "bg-blue-600", pillText: "text-white",
    label: "WATCH — Emerging", shortLabel: "Emerging",
  },
  WATCH_RELATIVE: {
    bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200",
    pillBg: "bg-sky-600", pillText: "text-white",
    label: "WATCH — Relative", shortLabel: "Relative",
  },
  WATCH_EARLY: {
    bg: "bg-indigo-50", text: "text-indigo-700", border: "border-indigo-200",
    pillBg: "bg-indigo-600", pillText: "text-white",
    label: "WATCH — Early", shortLabel: "Early",
  },
  AVOID: {
    bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200",
    pillBg: "bg-orange-500", pillText: "text-white",
    label: "AVOID", shortLabel: "AVOID",
  },
  SELL: {
    bg: "bg-red-50", text: "text-red-700", border: "border-red-200",
    pillBg: "bg-red-600", pillText: "text-white",
    label: "SELL", shortLabel: "SELL",
  },
};

const ACTION_ORDER: CompassAction[] = [
  "BUY", "SELL", "HOLD", "WATCH_EMERGING", "WATCH_RELATIVE", "WATCH_EARLY", "AVOID",
];

const ACTION_BADGE: Record<CompassAction, { bg: string; text: string }> = {
  BUY: { bg: "bg-emerald-100", text: "text-emerald-700" },
  HOLD: { bg: "bg-amber-100", text: "text-amber-700" },
  WATCH_EMERGING: { bg: "bg-blue-100", text: "text-blue-700" },
  WATCH_RELATIVE: { bg: "bg-sky-100", text: "text-sky-700" },
  WATCH_EARLY: { bg: "bg-indigo-100", text: "text-indigo-700" },
  AVOID: { bg: "bg-orange-100", text: "text-orange-700" },
  SELL: { bg: "bg-red-100", text: "text-red-700" },
};

// ── Kanban Card ────────────────────────────────────────

function KanbanCard({ sector: s, onClick }: { sector: SectorRS; onClick: () => void }) {
  const config = ACTION_CONFIG[s.action];
  return (
    <button
      onClick={onClick}
      className={`w-full text-left ${config.bg} rounded-xl border ${config.border} p-4 hover:shadow-md transition-shadow group`}
    >
      <div className="flex items-start justify-between mb-1">
        <div>
          <p className="text-sm font-bold text-slate-900">{s.display_name}</p>
          <span className={`${config.text} text-xs font-semibold`}>{config.label}</span>
        </div>
        <ArrowUpRight className="h-3.5 w-3.5 text-slate-300 group-hover:text-slate-500 shrink-0 mt-1" />
      </div>

      <div className="flex items-center gap-3 mt-2 flex-wrap">
        <span className="text-xs text-slate-500">
          RS <span className={`font-mono font-semibold ${s.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>
            {s.rs_score > 0 ? "+" : ""}{s.rs_score.toFixed(1)}%
          </span>
        </span>
        {s.absolute_return != null && (
          <span className={`text-xs font-mono ${s.absolute_return > 0 ? "text-emerald-600" : "text-red-600"}`}>
            Abs {s.absolute_return > 0 ? "+" : ""}{s.absolute_return.toFixed(1)}%
          </span>
        )}
        <span className={`text-xs font-mono ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
          Mom {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum.toFixed(1)}
        </span>
      </div>

      <div className="flex items-center gap-2 mt-2 flex-wrap">
        {s.pe_zone && (
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
            s.pe_zone === "VALUE" ? "bg-emerald-100 text-emerald-700" :
            s.pe_zone === "FAIR" ? "bg-slate-100 text-slate-600" :
            s.pe_zone === "STRETCHED" ? "bg-amber-100 text-amber-700" :
            "bg-red-100 text-red-700"
          }`}>
            {peZoneLabel(s.pe_zone, s.pe_ratio)}
          </span>
        )}
        {s.volume_signal && (
          <span className="text-xs text-slate-400">{volumeLabel(s.volume_signal)}</span>
        )}
        {!s.volume_signal && s.etfs.length === 0 && (
          <span className="text-xs text-slate-300 italic">No ETF mapped</span>
        )}
      </div>

      {s.action_reason && (
        <p className="text-xs text-slate-500 mt-2.5 leading-relaxed line-clamp-4">
          {s.action_reason}
        </p>
      )}
    </button>
  );
}

// ── Kanban View with Action Filters ────────────────────

function KanbanView({ sectors, onSectorClick }: { sectors: SectorRS[]; onSectorClick?: (k: string) => void }) {
  const [activeFilter, setActiveFilter] = useState<CompassAction | "ALL">("ALL");

  // Count per action
  const counts: Record<string, number> = {};
  for (const s of sectors) {
    counts[s.action] = (counts[s.action] || 0) + 1;
  }
  const activeActions = ACTION_ORDER.filter((a) => counts[a]);

  // Filter sectors
  const filtered = activeFilter === "ALL"
    ? sectors
    : sectors.filter((s) => s.action === activeFilter);

  const sorted = [...filtered].sort((a, b) => b.rs_score - a.rs_score);

  return (
    <div className="space-y-3">
      {/* Action filter pills */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          onClick={() => setActiveFilter("ALL")}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            activeFilter === "ALL"
              ? "bg-slate-800 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          All ({sectors.length})
        </button>
        {activeActions.map((action) => {
          const config = ACTION_CONFIG[action];
          const isActive = activeFilter === action;
          return (
            <button
              key={action}
              onClick={() => setActiveFilter(isActive ? "ALL" : action)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                isActive
                  ? `${config.pillBg} ${config.pillText}`
                  : `${config.bg} ${config.text} hover:opacity-80`
              }`}
            >
              {config.shortLabel} ({counts[action]})
            </button>
          );
        })}
      </div>

      {/* Cards grid — horizontal flow */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
        {sorted.map((s) => (
          <KanbanCard key={s.sector_key} sector={s} onClick={() => onSectorClick?.(s.sector_key)} />
        ))}
      </div>
    </div>
  );
}

// ── Table View ─────────────────────────────────────────

function TableView({ sectors, onSectorClick }: { sectors: SectorRS[]; onSectorClick?: (k: string) => void }) {
  const [activeFilter, setActiveFilter] = useState<CompassAction | "ALL">("ALL");

  const counts: Record<string, number> = {};
  for (const s of sectors) {
    counts[s.action] = (counts[s.action] || 0) + 1;
  }
  const activeActions = ACTION_ORDER.filter((a) => counts[a]);

  const filtered = activeFilter === "ALL"
    ? sectors
    : sectors.filter((s) => s.action === activeFilter);
  const sorted = [...filtered].sort((a, b) => b.rs_score - a.rs_score);

  return (
    <div className="space-y-3">
      {/* Action filter pills */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          onClick={() => setActiveFilter("ALL")}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            activeFilter === "ALL"
              ? "bg-slate-800 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          All ({sectors.length})
        </button>
        {activeActions.map((action) => {
          const config = ACTION_CONFIG[action];
          const isActive = activeFilter === action;
          return (
            <button
              key={action}
              onClick={() => setActiveFilter(isActive ? "ALL" : action)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                isActive
                  ? `${config.pillBg} ${config.pillText}`
                  : `${config.bg} ${config.text} hover:opacity-80`
              }`}
            >
              {config.shortLabel} ({counts[action]})
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Sector</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Action</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Relative Strength vs benchmark">RS %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Absolute return over period">Abs %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="4-week change in RS Score">Momentum</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Volume</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">P/E</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3 min-w-[280px]">Reason</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s) => {
                const badge = ACTION_BADGE[s.action] || ACTION_BADGE.HOLD;
                return (
                  <tr
                    key={s.sector_key}
                    onClick={() => onSectorClick?.(s.sector_key)}
                    className="border-b border-slate-50 hover:bg-slate-50 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-slate-900">{s.display_name}</p>
                      <p className="text-xs text-slate-400">{s.category}</p>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`${badge.bg} ${badge.text} rounded-full px-2 py-0.5 text-xs font-semibold`}>
                        {actionLabel(s.action)}
                      </span>
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${s.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {s.rs_score > 0 ? "+" : ""}{s.rs_score.toFixed(1)}%
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono ${(s.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {s.absolute_return != null ? `${s.absolute_return > 0 ? "+" : ""}${s.absolute_return.toFixed(1)}%` : "—"}
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum.toFixed(1)}
                    </td>
                    <td className="px-3 py-2.5 text-center text-xs" title={volumeDescription(s.volume_signal)}>
                      {s.volume_signal ? volumeDescription(s.volume_signal) : (s.etfs.length === 0 ? <span className="text-slate-300 italic">No ETF</span> : "—")}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">
                      {s.pe_ratio != null ? s.pe_ratio.toFixed(0) : "—"}
                      {s.pe_zone && <span className="text-xs text-slate-400 ml-1">· {s.pe_zone.charAt(0) + s.pe_zone.slice(1).toLowerCase()}</span>}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-slate-500 leading-relaxed">{s.action_reason}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────

interface Props {
  sectors: SectorRS[];
  onSectorClick?: (sectorKey: string) => void;
}

export function ActionSummary({ sectors, onSectorClick }: Props) {
  const [view, setView] = useState<"kanban" | "table">("kanban");

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Action Board</h3>
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5">
          <button
            onClick={() => setView("kanban")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
              view === "kanban" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <LayoutGrid className="h-3.5 w-3.5" /> Kanban
          </button>
          <button
            onClick={() => setView("table")}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
              view === "table" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <Table2 className="h-3.5 w-3.5" /> Table
          </button>
        </div>
      </div>

      {view === "kanban" ? (
        <KanbanView sectors={sectors} onSectorClick={onSectorClick} />
      ) : (
        <TableView sectors={sectors} onSectorClick={onSectorClick} />
      )}
    </div>
  );
}
