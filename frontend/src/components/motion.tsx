"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Subtle entrance animation (fade + slight rise). Used to add the "peak"
 * micro-interactions the UI/UX guidelines call for, without being flashy.
 */
export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut", delay }}
    >
      {children}
    </motion.div>
  );
}
