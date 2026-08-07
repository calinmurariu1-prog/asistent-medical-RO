"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import {
  Activity,
  CalendarDays,
  FileText,
  LayoutDashboard,
  LogOut,
  MapPin,
  MessageSquare,
  Pill,
  Stethoscope,
  User,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Spinner } from "@/components/ui";
import { ThemeToggle } from "@/components/theme-provider";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/labs", label: "Analize", icon: Activity },
  { href: "/documents", label: "Documente", icon: FileText },
  { href: "/chat", label: "Chat AI", icon: MessageSquare },
  { href: "/medications", label: "Medicamente", icon: Pill },
  { href: "/appointments", label: "Programări", icon: CalendarDays },
  { href: "/doctors", label: "Găsește medici", icon: MapPin },
  { href: "/profile", label: "Profil", icon: User },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) return <Spinner />;

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface p-4 sm:flex">
        <div className="mb-6 flex items-center gap-2 px-2 font-semibold">
          <Stethoscope className="text-brand-blue" size={20} />
          <span className="text-sm">Asistent Medical</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {nav.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
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

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border bg-surface px-6 py-3">
          <div className="text-sm text-muted">{user.email}</div>
          <ThemeToggle />
        </header>
        <main className="flex-1 overflow-x-hidden p-6">{children}</main>
      </div>
    </div>
  );
}
