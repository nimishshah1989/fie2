"use client";

interface ZoneScoreBoxProps {
  score: number;
  zone: string;
}

const ZONE_CONFIG: Record<string, {
  bg: string; border: string; text: string; bar: string;
  description: string;
}> = {
  Bear: {
    bg: "bg-red-50", border: "border-red-200", text: "text-red-700", bar: "bg-red-500",
    description: "Broad weakness across market. Majority of stocks below key moving averages.",
  },
  Weak: {
    bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", bar: "bg-amber-500",
    description: "Below-average market breadth. Participation declining across sectors.",
  },
  Neutral: {
    bg: "bg-slate-50", border: "border-slate-200", text: "text-slate-700", bar: "bg-slate-500",
    description: "Mixed signals. Neither broad strength nor widespread weakness.",
  },
  Bullish: {
    bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", bar: "bg-emerald-500",
    description: "Above-average breadth. Most stocks showing positive trends.",
  },
  Strong: {
    bg: "bg-emerald-100", border: "border-emerald-300", text: "text-emerald-800", bar: "bg-emerald-600",
    description: "Broad market strength. High participation across all technical layers.",
  },
};

const FALLBACK = ZONE_CONFIG.Neutral;

export function ZoneScoreBox({ score, zone }: ZoneScoreBoxProps) {
  const cfg = ZONE_CONFIG[zone] ?? FALLBACK;
  const clampedScore = Math.min(Math.max(score, 0), 100);

  return (
    <div className={`rounded-xl border ${cfg.border} ${cfg.bg} p-5 flex flex-col sm:flex-row sm:items-center gap-4`}>
      {/* Left: Score + Zone */}
      <div className="flex items-center gap-4 sm:w-40 shrink-0">
        <div>
          <p className={`text-4xl font-bold font-mono tabular-nums ${cfg.text}`}>
            {clampedScore.toFixed(0)}
          </p>
          <p className={`text-sm font-semibold ${cfg.text} mt-0.5`}>{zone} Market</p>
        </div>
      </div>

      {/* Right: Description + Progress */}
      <div className="flex-1 space-y-3">
        <p className="text-sm text-slate-600 leading-relaxed">{cfg.description}</p>
        <div className="space-y-1">
          <div className="w-full bg-white/50 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${cfg.bar}`}
              style={{ width: `${clampedScore}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 font-mono tabular-nums">
            <span>0</span>
            <span>50</span>
            <span>100</span>
          </div>
        </div>
      </div>
    </div>
  );
}
