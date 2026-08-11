"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  HeartPulse,
  LayoutDashboard,
  MessageSquare,
  Sparkles,
  User,
} from "lucide-react";

// Primary destinations for the mobile bottom tab bar (full list stays in the
// side drawer via the header menu button).
const tabs = [
  { href: "/dashboard", label: "Acasă", icon: LayoutDashboard },
  { href: "/health", label: "Sănătate", icon: HeartPulse },
  { href: "/assistant", label: "Asistent", icon: Sparkles },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/profile", label: "Profil", icon: User },
];

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="safe-b fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface/90 backdrop-blur sm:hidden">
      <div className="mx-auto flex max-w-lg items-stretch justify-around px-2">
        {tabs.map((t) => {
          const active = pathname.startsWith(t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition ${
                active ? "text-brand-blue" : "text-muted"
              }`}
            >
              <span
                className={`flex h-9 w-12 items-center justify-center rounded-full transition ${
                  active ? "brand-gradient text-white shadow-soft" : ""
                }`}
              >
                <t.icon size={19} />
              </span>
              {t.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
