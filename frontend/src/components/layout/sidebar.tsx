"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, Target, ScanLine, FileText, Terminal,
  Plus, Clock, CalendarDays, Shield, CheckSquare, Bell,
  Settings, HelpCircle, Sparkles,
} from "lucide-react";

const NAV_SECTIONS = [
  {
    title: "MAIN",
    items: [
      { name: "Dashboard",  href: "/dashboard", icon: LayoutDashboard },
      { name: "Scans",      href: "/scans",     icon: ScanLine },
      { name: "Targets",    href: "/targets",   icon: Target },
      { name: "Reports",    href: "/reports",   icon: FileText },
    ],
  },
  {
    title: "TOOLS & ANALYSE",
    items: [
      { name: "Kali Tools",   href: "/tools",   icon: Terminal,  badge: "tools_count" },
      { name: "AI Analyse",   href: "/reports", icon: Sparkles },
    ],
  },
  {
    title: "SCAN BEHEER",
    items: [
      { name: "Nieuwe Scan",      href: "/scans/new", icon: Plus,         highlight: true },
      { name: "Scan Geschiedenis", href: "/scans",     icon: Clock },
      { name: "Planning",          href: "/schedule",  icon: CalendarDays },
    ],
  },
  {
    title: "BEVEILIGING",
    items: [
      { name: "Audit Log",  href: "/audit",         icon: Shield },
      { name: "Compliance", href: "/compliance",    icon: CheckSquare },
      { name: "Meldingen",  href: "/notifications", icon: Bell },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [kaliOnline, setKaliOnline] = useState<boolean | null>(null);
  const [kaliVm, setKaliVm] = useState("");
  const [toolsCount, setToolsCount] = useState<number | null>(null);

  useEffect(() => {
    fetch("/api/tools/check")
      .then((r) => r.json())
      .then((d) => {
        setKaliOnline(d.reachable === true);
        setKaliVm(d.kali_vm || "");
      })
      .catch(() => setKaliOnline(false));

    fetch("/api/tools/available")
      .then((r) => r.json())
      .then((d) => setToolsCount(d.available_count ?? null))
      .catch(() => {});
  }, []);

  return (
    <div
      className="flex h-full w-[260px] flex-col"
      style={{ background: "#1d1d1f", color: "#f5f5f7" }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5" style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
        <div
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: "#0071e3" }}
        >
          <Shield className="h-4 w-4 text-white" />
        </div>
        <div>
          <p className="text-[15px] font-semibold" style={{ color: "#f5f5f7", letterSpacing: "-0.01em" }}>
            CyberPulse
          </p>
          <p className="text-[11px]" style={{ color: "rgba(245,245,247,0.4)" }}>
            Security Platform
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title}>
            <p
              className="px-3 mb-1.5 text-[10px] font-semibold tracking-widest"
              style={{ color: "rgba(245,245,247,0.3)" }}
            >
              {section.title}
            </p>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active =
                  item.href === "/scans"
                    ? pathname === "/scans" || (pathname.startsWith("/scans/") && !pathname.startsWith("/scans/new"))
                    : pathname === item.href || pathname.startsWith(item.href + "/");
                const Icon = item.icon;
                const count = item.badge === "tools_count" ? toolsCount : null;

                if (item.highlight) {
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-semibold transition-opacity hover:opacity-90"
                      style={{ background: "#0071e3", color: "#ffffff" }}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0" />
                      {item.name}
                    </Link>
                  );
                }

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors"
                    style={{
                      background: active ? "rgba(255,255,255,0.12)" : "transparent",
                      color: active ? "#ffffff" : "rgba(245,245,247,0.65)",
                    }}
                    onMouseEnter={(e) => {
                      if (!active) e.currentTarget.style.background = "rgba(255,255,255,0.06)";
                    }}
                    onMouseLeave={(e) => {
                      if (!active) e.currentTarget.style.background = "transparent";
                    }}
                  >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    <span className="flex-1">{item.name}</span>
                    {count !== null && (
                      <span
                        className="text-[10px] font-semibold rounded-full px-1.5 py-0.5"
                        style={{ background: "rgba(0,113,227,0.25)", color: "#4db8ff" }}
                      >
                        {count}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-3 pb-4 space-y-1" style={{ borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "12px" }}>
        {/* Kali VM status */}
        <div className="flex items-center gap-2 px-3 py-2">
          <span
            className="h-2 w-2 rounded-full flex-shrink-0"
            style={{
              background:
                kaliOnline === null ? "#ff9500" :
                kaliOnline ? "#34c759" : "#ff3b30",
              boxShadow: kaliOnline
                ? "0 0 6px rgba(52,199,89,0.5)"
                : undefined,
            }}
          />
          <div className="min-w-0">
            <p className="text-[12px]" style={{ color: "rgba(245,245,247,0.6)" }}>
              {kaliOnline === null ? "Verbinden..." : kaliOnline ? "Kali VM online" : "Kali VM offline"}
            </p>
            {kaliVm && kaliOnline && (
              <p
                className="text-[10px] truncate font-mono"
                style={{ color: "rgba(245,245,247,0.3)" }}
              >
                {kaliVm}
              </p>
            )}
          </div>
        </div>

        <Link
          href="/settings"
          className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors"
          style={{ color: "rgba(245,245,247,0.55)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          <Settings className="h-4 w-4" />
          Instellingen
        </Link>
        <Link
          href="/notifications"
          className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors"
          style={{ color: "rgba(245,245,247,0.55)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.06)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          <HelpCircle className="h-4 w-4" />
          Help
        </Link>
      </div>
    </div>
  );
}
