"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  LayoutDashboard, ScanLine, Target, FileText, Terminal,
  Plus, Database, GitCompare, Shield,
} from "lucide-react";

const NAV = [
  { name: "Dashboard",   href: "/dashboard",      icon: LayoutDashboard },
  { name: "Scans",       href: "/scans",          icon: ScanLine },
  { name: "New Scan",    href: "/scans/new",      icon: Plus },
  { name: "Targets",     href: "/targets",        icon: Target },
  { name: "Reports",     href: "/reports",        icon: FileText },
  { name: "Tools",       href: "/tools",          icon: Terminal },
  { name: "CVE Database", href: "/vulnerabilities", icon: Database },
  { name: "Compare",     href: "/compare",        icon: GitCompare },
];

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

  const isActive = (href: string) =>
    href === "/scans"
      ? pathname === "/scans" || (pathname.startsWith("/scans/") && !pathname.startsWith("/scans/new"))
      : pathname === href || pathname.startsWith(href + "/");

  return (
    <motion.aside
      onHoverStart={() => setExpanded(true)}
      onHoverEnd={() => setExpanded(false)}
      animate={{ width: expanded ? 240 : 64 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative z-20 flex h-screen flex-col border-r border-grid"
      style={{ background: "var(--bg-secondary)" }}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-[18px]">
        <div className="relative flex h-7 w-7 flex-shrink-0 items-center justify-center">
          <Shield className="h-6 w-6 text-cyan" style={{ filter: "drop-shadow(0 0 6px #00D4FF88)" }} />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-neon-green animate-pulse-dot" />
        </div>
        {expanded && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-display text-[16px] font-bold tracking-tight text-ink"
          >
            Cyber<span className="text-cyan">Pulse</span>
          </motion.span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-2 py-3">
        {NAV.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className="group relative flex h-10 items-center gap-3 rounded-md px-3 transition-colors"
              style={{
                background: active ? "rgba(0,212,255,0.08)" : "transparent",
                color: active ? "#00D4FF" : "#4A6880",
              }}
            >
              {active && (
                <span
                  className="absolute left-0 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded-r"
                  style={{ background: "#00D4FF", boxShadow: "0 0 8px #00D4FF" }}
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
            className={`h-2 w-2 flex-shrink-0 rounded-full ${kaliOnline ? "animate-pulse-dot" : ""}`}
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
