"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeInit() {
  // Applies the persisted theme before paint is handled by the inline script in
  // layout; this component only keeps <html> in sync on client navigation.
  useEffect(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "dark") document.documentElement.classList.add("dark");
  }, []);
  return null;
}

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  return (
    <button
      onClick={toggle}
      aria-label="Comută tema"
      className="shrink-0 rounded-lg border p-2 text-fg/70 transition hover:bg-bg hover:text-fg"
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
