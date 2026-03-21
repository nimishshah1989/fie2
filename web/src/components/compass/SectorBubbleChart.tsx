"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  ZAxis,
} from "recharts";
import type { SectorRS, Quadrant } from "@/lib/compass-types";

const QUADRANT_COLORS: Record<Quadrant, string> = {
  LEADING: "#059669",    // emerald-600
  IMPROVING: "#2563eb",  // blue-600
  WEAKENING: "#ea580c",  // orange-600
  LAGGING: "#dc2626",    // red-600
};

const QUADRANT_BG: Record<Quadrant, string> = {
  LEADING: "rgba(5,150,105,0.06)",
  IMPROVING: "rgba(37,99,235,0.06)",
  WEAKENING: "rgba(234,88,12,0.06)",
  LAGGING: "rgba(220,38,38,0.06)",
};

interface Props {
  sectors: SectorRS[];
  onSectorClick: (sectorKey: string) => void;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: SectorRS }> }) {
  if (!active || !payload?.[0]) return null;
  const s = payload[0].payload;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-slate-900">{s.display_name}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1.5">
        <span className="text-slate-500">RS Score</span>
        <span className={`font-mono font-medium text-right ${s.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {s.rs_score > 0 ? "+" : ""}{s.rs_score}%
        </span>
        <span className="text-slate-500">Momentum</span>
        <span className={`font-mono font-medium text-right ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum}
        </span>
        <span className="text-slate-500">Volume</span>
        <span className="font-medium text-right">{s.volume_signal?.replace("_", " ") || "—"}</span>
        <span className="text-slate-500">Action</span>
        <span className="font-semibold text-right" style={{ color: QUADRANT_COLORS[s.quadrant] }}>
          {s.action}
        </span>
        {s.etfs.length > 0 && (
          <>
            <span className="text-slate-500">ETF</span>
            <span className="font-medium text-right">{s.etfs.join(", ")}</span>
          </>
        )}
        {s.pe_ratio && (
          <>
            <span className="text-slate-500">P/E</span>
            <span className="font-mono text-right">{s.pe_ratio}</span>
          </>
        )}
      </div>
      <p className="text-xs text-slate-400 mt-2">Click to drill into stocks</p>
    </div>
  );
}

export function SectorBubbleChart({ sectors, onSectorClick }: Props) {
  // Transform data for scatter: bubble size = inverse P/E (lower PE = bigger)
  const chartData = sectors.map((s) => ({
    ...s,
    x: s.rs_score,
    y: s.rs_momentum,
    z: s.pe_ratio ? Math.max(5, 100 - s.pe_ratio) : 30, // default size if no PE
  }));

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <ResponsiveContainer width="100%" height={480}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            type="number"
            dataKey="x"
            name="RS Score"
            domain={["auto", "auto"]}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`}
            label={{ value: "RS Score (% vs Benchmark)", position: "bottom", offset: 0, style: { fontSize: 11, fill: "#64748b" } }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Momentum"
            domain={["auto", "auto"]}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}`}
            label={{ value: "Momentum (4w change)", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#64748b" } }}
          />
          <ZAxis type="number" dataKey="z" range={[200, 1200]} />
          <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="4 4" />
          <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={chartData}
            onClick={(data) => {
              if (data?.payload?.sector_key) {
                onSectorClick(data.payload.sector_key);
              }
            }}
            cursor="pointer"
          >
            {chartData.map((entry, i) => (
              <Cell
                key={`cell-${i}`}
                fill={QUADRANT_COLORS[entry.quadrant]}
                fillOpacity={0.7}
                stroke={QUADRANT_COLORS[entry.quadrant]}
                strokeWidth={entry.etfs.length > 0 ? 2 : 1}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Quadrant labels */}
      <div className="flex items-center justify-between px-6 -mt-2">
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-600 inline-block" /> LEADING
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-blue-600 inline-block" /> IMPROVING
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-orange-600 inline-block" /> WEAKENING
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-600 inline-block" /> LAGGING
          </span>
        </div>
        <p className="text-xs text-slate-400">Bubble size = Value (lower P/E = bigger)</p>
      </div>
    </div>
  );
}
