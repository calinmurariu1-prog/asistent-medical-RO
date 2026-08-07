"use client";

import { useId } from "react";

/**
 * Brand mark — "Puls & scânteie": an ECG pulse that resolves into an AI spark.
 * `mono` renders a single-color (currentColor) knockout version.
 */
export function LogoMark({
  size = 28,
  mono = false,
  className,
}: {
  size?: number;
  mono?: boolean;
  className?: string;
}) {
  const raw = useId().replace(/[:]/g, "");
  const gp = `p${raw}`;
  const gs = `s${raw}`;
  const stroke = mono ? "currentColor" : `url(#${gp})`;
  const sparkFill = mono ? "currentColor" : `url(#${gs})`;
  const dotFill = mono ? "currentColor" : "#10b981";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      role="img"
      aria-label="Asistent Medical AI"
      className={className}
    >
      {!mono && (
        <defs>
          <linearGradient id={gp} x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stopColor="#2563eb" />
            <stop offset="0.55" stopColor="#7c3aed" />
            <stop offset="1" stopColor="#10b981" />
          </linearGradient>
          <linearGradient id={gs} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#2563eb" />
            <stop offset="1" stopColor="#7c3aed" />
          </linearGradient>
        </defs>
      )}
      <path
        d="M5 29 H15 L19 18 L24 33 L27 24 H31"
        stroke={stroke}
        strokeWidth="3.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M37 12 l1.7 4.6 4.6 1.7 -4.6 1.7 -1.7 4.6 -1.7 -4.6 -4.6 -1.7 4.6 -1.7 z"
        fill={sparkFill}
      />
      <circle cx="31" cy="24" r="2.4" fill={dotFill} />
    </svg>
  );
}

/** Mark + wordmark lockup. */
export function LogoWord({ size = 26 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2 font-semibold">
      <LogoMark size={size} />
      <span>Asistent Medical AI</span>
    </div>
  );
}
