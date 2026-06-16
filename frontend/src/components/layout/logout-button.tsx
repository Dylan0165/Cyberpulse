"use client";

import { useState } from "react";
import { LogOut } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";

/**
 * Where to send the user after logging out (the marketing website).
 * - NEXT_PUBLIC_MARKETING_URL wins if set.
 * - On a bare IP / localhost (netlab + dev) the marketing site runs on :3100.
 * - Otherwise production: https://scanix.nl.
 */
function marketingUrl(): string {
  const env = process.env.NEXT_PUBLIC_MARKETING_URL;
  if (env) return env;
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isIpOrLocal =
      /^(\d{1,3}\.){3}\d{1,3}$/.test(host) || host === "localhost";
    if (isIpOrLocal) return `${window.location.protocol}//${host}:3100`;
  }
  return "https://scanix.nl";
}

export function LogoutButton() {
  const { user, logout } = useAuth();
  const [busy, setBusy] = useState(false);

  // Nothing to log out of when there's no real session.
  if (!user) return null;

  async function handleLogout() {
    setBusy(true);
    try {
      await logout();
    } catch {
      // best-effort — redirect regardless
    }
    window.location.href = marketingUrl();
  }

  return (
    <button
      onClick={handleLogout}
      disabled={busy}
      title="Uitloggen"
      className="inline-flex items-center gap-2 rounded-lg border border-grid bg-card2 px-3 py-1.5 text-[13px] font-medium text-ink-muted transition-colors hover:border-cyan/40 hover:text-ink disabled:opacity-50"
    >
      <LogOut className="h-4 w-4" />
      <span className="hidden sm:inline">{busy ? "Uitloggen..." : "Uitloggen"}</span>
    </button>
  );
}
