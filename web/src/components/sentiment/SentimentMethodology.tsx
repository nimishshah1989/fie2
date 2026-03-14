"use client";

import { useState } from "react";
import { Info, ChevronDown, ChevronRight } from "lucide-react";

const LAYERS = [
  { name: "Short-Term Trend", weight: "20%", metrics: [
    { name: "Above 10 EMA", desc: "% of stocks above 10-day exponential moving average. Measures very short-term momentum." },
    { name: "Above 21 EMA", desc: "% above 21-day EMA. Captures 1-month trend direction." },
    { name: "Above 50 EMA", desc: "% above 50-day EMA. Medium-term trend health." },
    { name: "52-Week High", desc: "% of stocks hitting new 52-week highs. Bullish breadth signal." },
    { name: "52-Week Low", desc: "% hitting new 52-week lows. Bearish breadth signal (inverted in scoring)." },
    { name: "MACD Bullish Cross", desc: "% with MACD histogram crossing above zero in last 5 days. Fresh momentum." },
    { name: "Daily RSI > 60", desc: "% with RSI above 60. Moderate momentum without being overbought." },
  ]},
  { name: "Broad Trend", weight: "30%", metrics: [
    { name: "Above 200 EMA", desc: "% above 200-day EMA. Long-term trend alignment." },
    { name: "Above 12 EMA (Monthly)", desc: "% above 12-month EMA. Intermediate trend." },
    { name: "Above 26 EMA (Monthly)", desc: "% above 26-month EMA. Long-term secular trend." },
    { name: "Monthly RSI > 50", desc: "% with monthly RSI above neutral. Upward bias." },
    { name: "Monthly RSI > 40", desc: "% with monthly RSI above 40. Excludes only deeply bearish stocks." },
    { name: "Weekly RSI > 50", desc: "% with weekly RSI above neutral. Short-term weekly trend." },
    { name: "Golden Cross", desc: "% where 50-day EMA is above 200-day EMA. Classic bullish formation." },
  ]},
  { name: "Advance/Decline", weight: "25%", metrics: [
    { name: "Prev Month High", desc: "% above previous calendar month's high. Monthly breakout breadth." },
    { name: "Prev Quarter High", desc: "% above previous quarter's high. Quarterly breakout breadth." },
    { name: "Prev Year High", desc: "% above previous year's high. Annual breakout breadth." },
    { name: "A/D Ratio", desc: "Market-wide advances to declines ratio from NSE live data." },
    { name: "52W High/Low Ratio", desc: "Ratio of stocks at 52-week highs vs lows." },
  ]},
  { name: "Momentum", weight: "15%", metrics: [
    { name: "3-Month High", desc: "% of stocks at 90-day highs. Medium-term momentum." },
    { name: "ROC > 0", desc: "% with positive 20-day rate of change. Directional momentum." },
    { name: "Higher Highs & Lows (10D)", desc: "% in strict 10-day uptrend pattern. Trend quality." },
  ]},
  { name: "Extremes", weight: "10%", metrics: [
    { name: "RSI Overbought (>70)", desc: "% with RSI above 70. Extended rally potential." },
    { name: "RSI Oversold (<30)", desc: "% with RSI below 30. Deep selloff (inverted in scoring)." },
    { name: "52W H/L Ratio", desc: "Breadth of highs vs lows at extremes." },
  ]},
];

const ZONES = [
  { zone: "Bear", range: "0 - 29", desc: "Broad weakness. Majority below key averages.", bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" },
  { zone: "Weak", range: "30 - 44", desc: "Below-average breadth. Participation declining.", bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500" },
  { zone: "Neutral", range: "45 - 54", desc: "Mixed signals. Neither strength nor weakness.", bg: "bg-slate-50", text: "text-slate-700", dot: "bg-slate-500" },
  { zone: "Bullish", range: "55 - 69", desc: "Above-average breadth. Positive trends dominating.", bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500" },
  { zone: "Strong", range: "70 - 100", desc: "Broad market strength. High participation across layers.", bg: "bg-emerald-100", text: "text-emerald-800", dot: "bg-emerald-600" },
];

function LayerDetail({ layer }: { layer: typeof LAYERS[number] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-blue-100 pt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs font-semibold text-blue-900 hover:text-blue-700 transition-colors w-full text-left"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {layer.name} ({layer.weight}) &mdash; {layer.metrics.length} metrics
      </button>
      {open && (
        <ul className="mt-2 ml-5 space-y-1.5">
          {layer.metrics.map((m) => (
            <li key={m.name} className="text-xs text-blue-800 leading-relaxed">
              <span className="font-medium text-blue-900">{m.name}:</span> {m.desc}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function SentimentMethodology() {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-5 py-3.5 text-left"
      >
        <Info className="h-4 w-4 text-blue-600 shrink-0" />
        <span className="text-sm font-semibold text-blue-900">How the Composite Score Works</span>
        {open
          ? <ChevronDown className="h-4 w-4 text-blue-500 ml-auto" />
          : <ChevronRight className="h-4 w-4 text-blue-500 ml-auto" />}
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-5">
          {/* Overview */}
          <p className="text-xs text-blue-800 leading-relaxed">
            The composite sentiment score (0-100) measures market breadth across 26 technical
            indicators grouped into 5 weighted layers:
          </p>

          {/* Layer weights table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-blue-200">
                  <th className="text-left py-1.5 font-semibold text-blue-900">Layer</th>
                  <th className="text-right py-1.5 font-semibold text-blue-900 w-20">Weight</th>
                  <th className="text-left py-1.5 pl-4 font-semibold text-blue-900">Focus</th>
                </tr>
              </thead>
              <tbody className="text-blue-800">
                <tr className="border-b border-blue-100"><td className="py-1.5">Short-Term Trend</td><td className="text-right font-mono tabular-nums">20%</td><td className="pl-4">Daily EMAs, 52-week highs/lows, MACD crossovers, daily RSI</td></tr>
                <tr className="border-b border-blue-100"><td className="py-1.5">Broad Trend</td><td className="text-right font-mono tabular-nums">30%</td><td className="pl-4">200 EMA, monthly EMAs, weekly/monthly RSI, Golden Cross</td></tr>
                <tr className="border-b border-blue-100"><td className="py-1.5">Advance/Decline</td><td className="text-right font-mono tabular-nums">25%</td><td className="pl-4">Breakouts above previous month/quarter/year highs, A/D ratio</td></tr>
                <tr className="border-b border-blue-100"><td className="py-1.5">Momentum</td><td className="text-right font-mono tabular-nums">15%</td><td className="pl-4">3-month highs, rate of change, uptrend patterns</td></tr>
                <tr><td className="py-1.5">Extremes</td><td className="text-right font-mono tabular-nums">10%</td><td className="pl-4">RSI overbought/oversold, 52-week high/low ratio</td></tr>
              </tbody>
            </table>
          </div>

          {/* Zone Definitions */}
          <div>
            <h4 className="text-sm font-semibold text-blue-900 mb-2">Zone Definitions</h4>
            <div className="space-y-1.5">
              {ZONES.map((z) => (
                <div key={z.zone} className={`flex items-center gap-3 px-3 py-2 rounded-lg ${z.bg}`}>
                  <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${z.dot}`} />
                  <span className={`text-xs font-semibold w-16 ${z.text}`}>{z.zone}</span>
                  <span className="text-xs font-mono tabular-nums text-blue-800 w-16">{z.range}</span>
                  <span className="text-xs text-blue-800 flex-1">{z.desc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Indicator Reference */}
          <div>
            <h4 className="text-sm font-semibold text-blue-900 mb-2">Indicator Reference</h4>
            <div className="space-y-2">
              {LAYERS.map((layer) => (
                <LayerDetail key={layer.name} layer={layer} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
