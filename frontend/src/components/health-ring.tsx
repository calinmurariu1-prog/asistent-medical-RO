"use client";

import { motion } from "framer-motion";

/**
 * A soft circular progress ring for a health metric (steps, sleep, SpO₂, …).
 * `value`/`goal` drive the arc; `color` is a CSS color (brand tokens work).
 */
export function HealthRing({
  value,
  goal,
  label,
  unit,
  color = "rgb(var(--brand-blue))",
  size = 92,
  displayValue,
}: {
  value: number;
  goal: number;
  label: string;
  unit?: string;
  color?: string;
  size?: number;
  displayValue?: string;
}) {
  const stroke = 9;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = goal > 0 ? Math.max(0, Math.min(1, value / goal)) : 0;
  const display =
    displayValue ??
    (value >= 1000 ? `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k` : `${value}`);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="rgb(var(--border))"
            strokeWidth={stroke}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            initial={{ strokeDashoffset: c }}
            animate={{ strokeDashoffset: c * (1 - pct) }}
            transition={{ duration: 0.9, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold leading-none tabular-nums">
            {display}
          </span>
          {unit && <span className="text-[10px] text-muted">{unit}</span>}
        </div>
      </div>
      <span className="text-xs font-medium text-muted">{label}</span>
    </div>
  );
}
