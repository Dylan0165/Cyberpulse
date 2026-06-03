"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Target,
  ScanLine,
  FileText,
  Wrench,
  Shield,
} from "lucide-react";

const NAV = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Scans",     href: "/scans",     icon: ScanLine },
  { name: "Targets",   href: "/targets",   icon: Target },
  { name: "Tools",     href: "/tools",     icon: Wrench },
  { name: "Reports",   href: "/reports",   icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const [kaliStatus, setKaliStatus] = useState<"loading" | "online" | "offline">("loading");
  const [kaliVm, setKaliVm] = useState("");

  useEffect(() => {
    fetch("/api/tools/check")
      .then((r) => r.json())
      .then((d) => {
        setKaliStatus(d.reachable ? "online" : "offline");
        setKaliVm(d.kali_vm || "");
      })
      .catch(() => setKaliStatus("offline"));
  }, []);

  return (
    <div className="flex h-full w-[240px] flex-col border-r border-border bg-card">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-6 py-5 border-b border-border">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/15">
          <Shield className="h-4 w-4 text-primary" />
        </div>
        <span className="text-[15px] font-semibold tracking-tight text-foreground">
          CyberPulse
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Kali VM status */}
      <div className="px-5 py-4 border-t border-border">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full flex-shrink-0 ${
              kaliStatus === "online"
                ? "bg-emerald-500"
                : kaliStatus === "offline"
                ? "bg-red-500"
                : "bg-yellow-500 animate-pulse"
            }`}
          />
          <span className="text-xs text-muted-foreground">
            {kaliStatus === "loading"
              ? "Verbinden..."
              : kaliStatus === "online"
              ? `Kali VM online`
              : "Kali VM offline"}
          </span>
        </div>
        {kaliVm && kaliStatus === "online" && (
          <p className="text-[11px] text-muted-foreground/50 mt-0.5 pl-4 font-mono">{kaliVm}</p>
        )}
      </div>
    </div>
  );
}
