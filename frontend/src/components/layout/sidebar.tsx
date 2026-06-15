"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  LayoutDashboard, Radar, Target, FileText, Calendar,
  Wrench, Settings, Shield, Sparkles,
} from "lucide-react";

const NAV = [
  { name: "Overzicht",          href: "/dashboard", icon: LayoutDashboard },
  { name: "Beveiligingstests",  href: "/scans",     icon: Radar },
  { name: "Mijn systemen",      href: "/targets",   icon: Target },
  { name: "Rapporten",          href: "/reports",   icon: FileText },
  { name: "Automatische tests", href: "/schedule",  icon: Calendar },
  { name: "Tools",              href: "/tools",     icon: Wrench },
  { name: "AI Upgraden",        href: "/upgrade",   icon: Sparkles },
  { name: "Instellingen",       href: "/settings",  icon: Settings },
];

const MOBILE_NAV = [
  { name: "Overzicht",         href: "/dashboard", icon: LayoutDashboard },
  { name: "Beveiligingstests", href: "/scans",     icon: Radar },
  { name: "Mijn systemen",     href: "/targets",   icon: Target },
  { name: "Rapporten",         href: "/reports",   icon: FileText },
  { name: "Instellingen",      href: "/settings",  icon: Settings },
];

const isActive = (pathname: string, href: string) =>
  pathname === href || pathname.startsWith(href + "/");

export function Sidebar() {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(false);
  const [kaliOnline, setKaliOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/tools/available", { cache: "no-store" })
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d) => setKaliOnline(Array.isArray(d.tools)))
      .catch(() => setKaliOnline(false));
  }, []);

  return (
    <motion.aside
      onHoverStart={() => setExpanded(true)}
      onHoverEnd={() => setExpanded(false)}
      animate={{ width: expanded ? 240 : 64 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative z-20 hidden h-screen flex-col border-r border-grid md:flex"
      style={{ background: "var(--bg-secondary)" }}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-[18px]">
        <div className="relative flex h-7 w-7 flex-shrink-0 items-center justify-center">
          <Shield className="h-6 w-6 text-cyan" />
          <span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-neon-green" />
        </div>
        {expanded && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-display text-[16px] font-bold tracking-tight text-ink"
          >
            Scan<span className="text-cyan">ix</span>
          </motion.span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-2 py-3">
        {NAV.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className="group relative flex h-10 items-center gap-3 rounded-md px-3 transition-colors"
              style={{
                background: active ? "rgba(0,180,216,0.05)" : "transparent",
                color: active ? "#00B4D8" : "#4A6880",
                opacity: active ? 1 : 0.7,
              }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.opacity = "1"; }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.opacity = "0.7"; }}
            >
              {active && (
                <span
                  className="absolute left-0 top-1/2 h-6 w-[2px] -translate-y-1/2"
                  style={{ background: "#00B4D8" }}
                />
              )}
              <Icon className="h-[18px] w-[18px] flex-shrink-0 transition-colors group-hover:text-cyan" />
              {expanded ? (
                <motion.span
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="whitespace-nowrap text-[13px] font-medium"
                >
                  {item.name}
                </motion.span>
              ) : (
                <span className="pointer-events-none absolute left-[60px] z-50 whitespace-nowrap rounded-md border border-grid bg-card2 px-2.5 py-1 text-[12px] font-medium text-ink opacity-0 shadow-glow-cyan transition-opacity group-hover:opacity-100">
                  {item.name}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Kali VM status */}
      <div className="border-t border-grid px-3 py-4">
        <div className="flex items-center gap-2.5">
          <span
            className="h-1.5 w-1.5 flex-shrink-0 rounded-full"
            style={{ background: kaliOnline === null ? "#FF8C00" : kaliOnline ? "#00FF88" : "#FF2D55" }}
          />
          {expanded && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <p className="font-mono text-[10px] uppercase tracking-wider" style={{ color: kaliOnline ? "#00FF88" : "#FF2D55" }}>
                {kaliOnline === null ? "connecting" : kaliOnline ? "kali vm online" : "kali vm offline"}
              </p>
              <p className="font-mono text-[10px] text-ink-muted">192.168.121.28</p>
            </motion.div>
          )}
        </div>
      </div>
    </motion.aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-30 flex h-[60px] items-stretch md:hidden"
      style={{
        background: "var(--bg-secondary)",
        borderTop: "1px solid var(--border)",
      }}
    >
      {MOBILE_NAV.map((item) => {
        const active = isActive(pathname, item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.name}
            href={item.href}
            className="flex flex-1 flex-col items-center justify-center gap-1 transition-colors"
            style={{ color: active ? "#00D4FF" : "#4A6880" }}
          >
            <Icon className="h-[20px] w-[20px]" />
            <span className="text-[10px] font-medium">{item.name}</span>
          </Link>
        );
      })}
    </nav>
  );
}
