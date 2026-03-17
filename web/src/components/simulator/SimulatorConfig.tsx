"use client";

import { Play, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Strategy, MutualFund, MetricInfo } from "@/lib/simulator-types";
import { cn } from "@/lib/utils";

const MULTIPLIER_OPTIONS = [1, 1.5, 2, 3, 4, 5];
const DURATION_OPTIONS = [
  { label: "1 Year", value: 12 },
  { label: "2 Years", value: 24 },
  { label: "3 Years", value: 36 },
  { label: "5 Years", value: 60 },
  { label: "Till Date", value: 0 },
];

interface Props {
  fund: MutualFund;
  strategy: Strategy;
  metric: string;
  setMetric: (v: string) => void;
  threshold: number;
  setThreshold: (v: number) => void;
  sipAmount: number;
  setSipAmount: (v: number) => void;
  multiplier: number;
  setMultiplier: (v: number) => void;
  durationMonths: number;
  setDurationMonths: (v: number) => void;
  running: boolean;
  metrics: MetricInfo[];
  thresholds: number[];
  onRun: () => void;
  onClose: () => void;
}

export function SimulatorConfig({
  fund, strategy, metric, setMetric, threshold, setThreshold,
  sipAmount, setSipAmount, multiplier, setMultiplier,
  durationMonths, setDurationMonths, running, metrics, thresholds,
  onRun, onClose,
}: Props) {
  return (
    <div className="bg-white rounded-xl border border-teal-200 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-bold text-slate-800">
            {fund.name.replace(" - Direct Growth", "")}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">Custom simulation — pick any metric + threshold</p>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
          <X className="size-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {/* Metric dropdown */}
        <div>
          <Label className="text-[10px] text-slate-500 mb-1 block">Breadth Metric</Label>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="w-full h-8 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
          >
            {metrics.map((m) => (
              <option key={m.key} value={m.key}>{m.label}</option>
            ))}
          </select>
        </div>

        {/* Threshold buttons */}
        <div>
          <Label className="text-[10px] text-slate-500 mb-1 block">Threshold (≤)</Label>
          <div className="flex gap-1 flex-wrap">
            {thresholds.map((t) => (
              <button
                key={t} type="button"
                onClick={() => setThreshold(t)}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-medium border font-mono",
                  threshold === t
                    ? "bg-teal-600 text-white border-teal-600"
                    : "bg-white text-slate-500 border-slate-200 hover:border-teal-400"
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* SIP Amount */}
        <div>
          <Label className="text-[10px] text-slate-500 mb-1 block">SIP ₹/month</Label>
          <Input
            type="number"
            value={sipAmount}
            onChange={(e) => setSipAmount(Number(e.target.value))}
            min={500} step={500}
            className="font-mono h-8 text-xs"
          />
        </div>

        {/* Multiplier */}
        <div>
          <Label className="text-[10px] text-slate-500 mb-1 block">Multiplier</Label>
          <div className="flex gap-1 flex-wrap">
            {MULTIPLIER_OPTIONS.map((m) => (
              <button
                key={m} type="button"
                onClick={() => setMultiplier(m)}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-medium border",
                  multiplier === m
                    ? "bg-teal-600 text-white border-teal-600"
                    : "bg-white text-slate-500 border-slate-200 hover:border-teal-400"
                )}
              >
                {m}x
              </button>
            ))}
          </div>
        </div>

        {/* Duration */}
        <div>
          <Label className="text-[10px] text-slate-500 mb-1 block">Duration</Label>
          <select
            value={durationMonths}
            onChange={(e) => setDurationMonths(Number(e.target.value))}
            className="w-full h-8 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-700"
          >
            {DURATION_OPTIONS.map((d) => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>

        {/* Run button */}
        <div className="flex items-end">
          <Button
            onClick={onRun} disabled={running}
            className="w-full h-8 bg-teal-600 text-white hover:bg-teal-700 text-xs gap-1.5"
          >
            {running ? <Loader2 className="size-3 animate-spin" /> : <Play className="size-3" />}
            {running ? "Running..." : "Simulate"}
          </Button>
        </div>
      </div>
    </div>
  );
}
