"use client";

import { useId } from "react";

export interface ChartPoint {
  label: string; // x-axis label (e.g. a date)
  value: number;
}

/** Tiny label-free line+area chart for compact spaces (e.g. under a ring). */
export function Sparkline({
  values,
  color = "#ffffff",
  width = 120,
  height = 32,
}: {
  values: number[];
  color?: string;
  width?: number;
  height?: number;
}) {
  const gid = useId().replace(/[:]/g, "");
  if (values.length < 2) return null;
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const x = (i: number) => (i * width) / (values.length - 1);
  const y = (v: number) => height - 3 - ((v - min) * (height - 6)) / (max - min);
  const line = values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  const area = `0,${height} ${line} ${width},${height}`;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height}>
      <defs>
        <linearGradient id={`s${gid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.5" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#s${gid})`} />
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Lightweight responsive line/area chart (pure SVG, no dependencies).
 * Optionally draws a reference band (refLow–refHigh) for lab values.
 */
export function LineChart({
  points,
  unit,
  refLow,
  refHigh,
  color = "rgb(var(--brand-blue))",
  height = 160,
}: {
  points: ChartPoint[];
  unit?: string | null;
  refLow?: number | null;
  refHigh?: number | null;
  color?: string;
  height?: number;
}) {
  const gid = useId().replace(/[:]/g, "");
  const W = 600;
  const H = height;
  const padX = 40;
  const padY = 20;

  const values = points.map((p) => p.value);
  const candidates = [...values];
  if (refLow != null) candidates.push(refLow);
  if (refHigh != null) candidates.push(refHigh);
  let min = Math.min(...candidates);
  let max = Math.max(...candidates);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const span = max - min;
  min -= span * 0.1;
  max += span * 0.1;

  const x = (i: number) =>
    points.length <= 1
      ? W / 2
      : padX + (i * (W - 2 * padX)) / (points.length - 1);
  const y = (v: number) => padY + ((max - v) * (H - 2 * padY)) / (max - min);

  const line = points.map((p, i) => `${x(i)},${y(p.value)}`).join(" ");
  const area = `${padX},${H - padY} ${line} ${x(points.length - 1)},${H - padY}`;

  const last = points[points.length - 1];

  return (
    <svg role="img" aria-label="Evoluția valorilor în timp" aria-describedby={`values${gid}`} viewBox={`0 0 ${W} ${H}`} width="100%" className="overflow-visible">
      <desc id={`values${gid}`}>{points.map(p => `${p.label}: ${p.value} ${unit || ""}`).join("; ")}</desc>
      <defs>
        <linearGradient id={`fill${gid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.22" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Reference band */}
      {refLow != null && refHigh != null && (
        <rect
          x={padX}
          y={y(refHigh)}
          width={W - 2 * padX}
          height={Math.max(0, y(refLow) - y(refHigh))}
          fill="rgb(var(--brand-green))"
          opacity="0.10"
        />
      )}

      {/* min/max gridlines */}
      {[max - (max - min) * 0.1, min + (max - min) * 0.1].map((v, i) => (
        <g key={i}>
          <line
            x1={padX}
            x2={W - padX}
            y1={y(v)}
            y2={y(v)}
            stroke="rgb(var(--border))"
            strokeDasharray="3 4"
          />
          <text x={4} y={y(v) + 4} fontSize="12" fill="rgb(var(--muted))">
            {Math.round(v * 10) / 10}
          </text>
        </g>
      ))}

      {points.length > 1 && (
        <polygon points={area} fill={`url(#fill${gid})`} />
      )}
      {points.length > 1 && (
        <polyline
          points={line}
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {points.map((p, i) => (
        <circle
          key={i}
          cx={x(i)}
          cy={y(p.value)}
          r={i === points.length - 1 ? 4.5 : 3}
          fill={color}
        />
      ))}

      {/* last value label */}
      <text
        x={x(points.length - 1)}
        y={y(last.value) - 10}
        fontSize="13"
        fontWeight="700"
        textAnchor="end"
        fill="rgb(var(--fg))"
      >
        {last.value}
        {unit ? ` ${unit}` : ""}
      </text>

      {/* first/last x labels */}
      <text x={padX} y={H - 4} fontSize="11" fill="rgb(var(--muted))">
        {points[0].label}
      </text>
      {points.length > 1 && (
        <text
          x={W - padX}
          y={H - 4}
          fontSize="11"
          textAnchor="end"
          fill="rgb(var(--muted))"
        >
          {last.label}
        </text>
      )}
    </svg>
  );
}
