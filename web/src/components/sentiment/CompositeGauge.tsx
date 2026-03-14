"use client";

interface CompositeGaugeProps {
  score: number;
  zone: string;
}

const SEGMENTS = [
  { label: "Bear", max: 20, color: "#e24b4a", startDeg: 180, endDeg: 144 },
  { label: "Weak", max: 45, color: "#ef9f27", startDeg: 144, endDeg: 99 },
  { label: "Neutral", max: 55, color: "#888780", startDeg: 99, endDeg: 81 },
  { label: "Bullish", max: 70, color: "#1d9e75", startDeg: 81, endDeg: 54 },
  { label: "Strong", max: 100, color: "#3b6d11", startDeg: 54, endDeg: 0 },
];

function polarToCartesian(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const start = polarToCartesian(cx, cy, r, startDeg);
  const end = polarToCartesian(cx, cy, r, endDeg);
  const largeArc = startDeg - endDeg > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export function CompositeGauge({ score, zone }: CompositeGaugeProps) {
  const cx = 130;
  const cy = 130;
  const r = 88;
  // Needle angle: score 0 → 180°, score 100 → 0°
  const needleDeg = 180 - Math.min(Math.max(score, 0), 100) * 1.8;
  const needleTip = polarToCartesian(cx, cy, r - 12, needleDeg);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 260 150" className="w-full max-w-[260px]">
        {/* Arc segments */}
        {SEGMENTS.map((seg) => (
          <path
            key={seg.label}
            d={arcPath(cx, cy, r, seg.startDeg, seg.endDeg)}
            fill="none"
            stroke={seg.color}
            strokeWidth={14}
            strokeLinecap="butt"
          />
        ))}
        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={needleTip.x}
          y2={needleTip.y}
          stroke="#334155"
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={5} fill="#334155" />
        {/* Score */}
        <text
          x={cx}
          y={105}
          textAnchor="middle"
          className="font-mono"
          fontSize={34}
          fontWeight={700}
          fill="#1e293b"
        >
          {score.toFixed(0)}
        </text>
        {/* Zone label */}
        <text
          x={cx}
          y={122}
          textAnchor="middle"
          fontSize={12}
          fill="#64748b"
        >
          {zone}
        </text>
      </svg>
    </div>
  );
}
