"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Target,
  Scan,
  FileText,
  Settings,
  Wrench,
  Server,
  CalendarDays,
  MessageSquare,
  Shield,
  GitCompare,
  Plug,
  History,
  Bell,
} from "lucide-react";

const navItems = [
  { section: "Algemeen" },
  { name: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
  { name: "Targets", href: "/targets", icon: "Target" },
  { name: "Scans", href: "/scans", icon: "Scan" },
  { name: "Assets", href: "/assets", icon: "Server" },
  { name: "Planning", href: "/schedule", icon: "CalendarDays" },
  { section: "Analyse" },
  { name: "AI Chat", href: "/chat", icon: "MessageSquare" },
  { name: "Compliance", href: "/compliance", icon: "Shield" },
  { name: "Vergelijken", href: "/compare", icon: "GitCompare" },
  { name: "Reports", href: "/reports", icon: "FileText" },
  { section: "Beheer" },
  { name: "Tools", href: "/tools", icon: "Wrench" },
  { name: "Integraties", href: "/integrations", icon: "Plug" },
  { name: "Meldingen", href: "/notifications", icon: "Bell" },
  { name: "Audit Log", href: "/audit", icon: "History" },
  { name: "Settings", href: "/settings", icon: "Settings" },
];

const ICONS: Record<string, React.ElementType> = {
  LayoutDashboard, Target, Scan, FileText, Settings, Wrench,
  Server, CalendarDays, MessageSquare, Shield, GitCompare, Plug, History, Bell,
};

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-[220px] flex-col border-r bg-card">
      <div className="px-6 pt-6 pb-4">
        <span className="text-[15px] font-bold tracking-[0.15em] uppercase text-foreground">
          Cyber<span className="font-normal text-muted-foreground">Pulse</span>
        </span>
      </div>

      <nav className="flex-1 flex flex-col gap-0 overflow-y-auto pb-2">
        {navItems.map((item, i) => {
          if ("section" in item) {
            return (
              <div key={`s-${i}`} className="px-6 pt-4 pb-1 text-[9px] font-bold uppercase tracking-[0.12em] text-muted-foreground/50">
                {item.section}
              </div>
            );
          }
          const Icon = ICONS[item.icon];
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-2 px-6 py-2 text-[12px] font-medium uppercase tracking-[0.05em] border-l-2 transition-colors ${
                isActive
                  ? "border-foreground text-foreground bg-secondary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              {Icon && <Icon className="h-4 w-4 flex-shrink-0" />}
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-6 py-4 text-[10px] text-muted-foreground leading-[1.8]">
        <span className="inline-block h-[6px] w-[6px] rounded-full bg-green-500 mr-1" />
        Engine online
        <br />
        <span className="opacity-50">N scan · T tools · H home</span>
      </div>
    </div>
  );
}
