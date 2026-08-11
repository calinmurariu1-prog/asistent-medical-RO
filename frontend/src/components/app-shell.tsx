"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  Activity,
  CalendarDays,
  CreditCard,
  FileText,
  HeartPulse,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  MessageSquare,
  Pill,
  Sparkles,
  User,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useNativeShell } from "@/lib/native";
import { useHealthAutoSync } from "@/lib/health-native";
import { Spinner } from "@/components/ui";
import { LogoMark } from "@/components/logo";
import { BottomNav } from "@/components/bottom-nav";
import { ThemeToggle } from "@/components/theme-provider";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/labs", label: "Analize", icon: Activity },
  { href: "/health", label: "Date de sănătate", icon: HeartPulse },
  { href: "/documents", label: "Documente", icon: FileText },
  { href: "/chat", label: "Chat AI", icon: MessageSquare },
  { href: "/assistant", label: "Asistent AI", icon: Sparkles },
  { href: "/medications", label: "Medicamente", icon: Pill },
  { href: "/appointments", label: "Programări", icon: CalendarDays },
  { href: "/doctors", label: "Găsește medici", icon: MapPin },
  { href: "/subscription", label: "Abonament", icon: CreditCard },
  { href: "/profile", label: "Profil", icon: User },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  useNativeShell();
  useHealthAutoSync(); // native: auto-import wearable data on open/resume

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (loading || !user) return <Spinner />;

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 sm:hidden"
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 flex-col border-r border-border bg-surface p-4 transition-transform sm:static sm:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-6 flex items-center gap-2 px-2 font-semibold">
          <LogoMark size={22} />
          <span className="text-sm">Asistent Medical</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto">
          {nav.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                  active
                    ? "brand-gradient text-white"
                    : "text-fg/70 hover:bg-bg hover:text-fg"
                }`}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={logout}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-fg/70 transition hover:bg-bg hover:text-fg"
        >
          <LogOut size={18} />
          Deconectare
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border/70 bg-surface px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              aria-label="Deschide meniul"
              className="rounded-xl border border-border p-2 text-fg/70 transition hover:bg-surface-2 sm:hidden"
            >
              <Menu size={18} />
            </button>
            <div className="truncate text-sm text-muted">{user.email}</div>
          </div>
          <ThemeToggle />
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden p-4 pb-24 sm:p-6 sm:pb-6">
          {children}
        </main>
      </div>

      <BottomNav />
    </div>
  );
}
