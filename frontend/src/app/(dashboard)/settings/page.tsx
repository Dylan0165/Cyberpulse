"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  User,
  Bell,
  Key,
  Server,
  Save,
  Eye,
  EyeOff,
  RefreshCw,
  Plug,
  CheckCircle2,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";

type TabId = "account" | "notifications" | "apikey" | "kali";

const TABS: { id: TabId; label: string; icon: LucideIcon }[] = [
  { id: "account", label: "Account", icon: User },
  { id: "notifications", label: "Notificaties", icon: Bell },
  { id: "apikey", label: "API Sleutel", icon: Key },
  { id: "kali", label: "Kali VM", icon: Server },
];

const inputCls =
  "w-full rounded-lg border border-grid bg-app px-3 py-2 text-[13px] text-ink placeholder:text-ink-muted/60 outline-none transition-colors focus:border-cyan focus:shadow-glow-cyan font-mono";

const labelCls =
  "mb-1.5 block text-[11px] uppercase tracking-[0.1em] text-ink-muted";

function PrimaryButton({
  children,
  onClick,
  type = "button",
  disabled,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-2 rounded-lg border border-cyan/40 bg-cyan/10 px-4 py-2 text-[13px] font-medium text-cyan transition-all hover:bg-cyan/20 hover:shadow-glow-cyan disabled:cursor-not-allowed disabled:opacity-40"
    >
      {children}
    </button>
  );
}

export default function SettingsPage() {
  const [tab, setTab] = useState<TabId>("account");

  // Account (UI-only)
  const [account, setAccount] = useState({
    name: "",
    email: "",
    company: "",
  });

  // Notifications (UI-only)
  const [notifyOn, setNotifyOn] = useState(false);
  const [notifyEmail, setNotifyEmail] = useState("");

  // API key (UI-only)
  const [keyRevealed, setKeyRevealed] = useState(false);
  const apiKey = "sk-a91f0c4d7e2b88f3a1d6e09c4b2f3f8a";
  const maskedKey = "sk-••••••••••••3f8a";

  // Kali VM
  const [kaliIp, setKaliIp] = useState("192.168.121.28");
  const [kaliPort, setKaliPort] = useState("5001");
  const [conn, setConn] = useState<"idle" | "testing" | "ok" | "fail">("idle");
  const [toolCount, setToolCount] = useState<number | null>(null);

  async function testConnection() {
    setConn("testing");
    setToolCount(null);
    try {
      const res = await fetch("/api/tools/available");
      if (!res.ok) throw new Error("bad response");
      const data: unknown = await res.json();
      const tools = Array.isArray(data)
        ? data
        : Array.isArray((data as { tools?: unknown[] })?.tools)
        ? (data as { tools: unknown[] }).tools
        : null;
      if (!tools) throw new Error("no tools");
      setToolCount(tools.length);
      setConn("ok");
    } catch {
      setConn("fail");
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-[0.02em] text-ink">
          Instellingen
        </h1>
        <p className="mt-1 text-[13px] text-ink-muted">
          Beheer uw account en systeeminstellingen
        </p>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-[12px] font-medium transition-all ${
                active
                  ? "border-cyan/50 bg-cyan/10 text-cyan shadow-glow-cyan"
                  : "border-grid bg-card2 text-ink-muted hover:border-cyan/30 hover:text-ink"
              }`}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ── Account ── */}
      {tab === "account" && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <GlowCard className="p-6">
            <div className="mb-5 flex items-center gap-2">
              <User className="h-4 w-4 text-cyan" />
              <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">
                Accountgegevens
              </h2>
            </div>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label className={labelCls}>Naam</label>
                <input
                  className={inputCls}
                  value={account.name}
                  onChange={(e) =>
                    setAccount({ ...account, name: e.target.value })
                  }
                  placeholder="Jan Jansen"
                />
              </div>
              <div>
                <label className={labelCls}>E-mailadres</label>
                <input
                  className={inputCls}
                  type="email"
                  value={account.email}
                  onChange={(e) =>
                    setAccount({ ...account, email: e.target.value })
                  }
                  placeholder="jan@bedrijf.nl"
                />
              </div>
              <div className="md:col-span-2">
                <label className={labelCls}>Bedrijfsnaam</label>
                <input
                  className={inputCls}
                  value={account.company}
                  onChange={(e) =>
                    setAccount({ ...account, company: e.target.value })
                  }
                  placeholder="CyberPulse B.V."
                />
              </div>
            </div>
            <div className="mt-6">
              <PrimaryButton
                onClick={() => toast.success("Instellingen opgeslagen")}
              >
                <Save className="h-4 w-4" />
                Opslaan
              </PrimaryButton>
            </div>
          </GlowCard>
        </motion.div>
      )}

      {/* ── Notificaties ── */}
      {tab === "notifications" && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <GlowCard className="p-6">
            <div className="mb-5 flex items-center gap-2">
              <Bell className="h-4 w-4 text-cyan" />
              <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">
                Notificaties
              </h2>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-grid bg-app px-4 py-3">
              <div>
                <div className="text-[13px] text-ink">
                  E-mail bij voltooide scan
                </div>
                <div className="text-[11px] text-ink-muted">
                  Ontvang een bericht zodra een scan klaar is
                </div>
              </div>
              <button
                role="switch"
                aria-checked={notifyOn}
                onClick={() => setNotifyOn((v) => !v)}
                className={`relative h-6 w-11 rounded-full border transition-colors ${
                  notifyOn
                    ? "border-cyan bg-cyan/30"
                    : "border-grid bg-card2"
                }`}
              >
                <motion.span
                  layout
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                  className={`absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full ${
                    notifyOn
                      ? "right-1 bg-cyan shadow-glow-cyan"
                      : "left-1 bg-ink-muted"
                  }`}
                />
              </button>
            </div>

            {notifyOn && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="mt-5 overflow-hidden"
              >
                <label className={labelCls}>E-mailadres voor notificaties</label>
                <input
                  className={inputCls}
                  type="email"
                  value={notifyEmail}
                  onChange={(e) => setNotifyEmail(e.target.value)}
                  placeholder="alerts@bedrijf.nl"
                />
              </motion.div>
            )}

            <div className="mt-6">
              <PrimaryButton
                onClick={() => toast.success("Instellingen opgeslagen")}
              >
                <Save className="h-4 w-4" />
                Opslaan
              </PrimaryButton>
            </div>
          </GlowCard>
        </motion.div>
      )}

      {/* ── API Sleutel ── */}
      {tab === "apikey" && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <GlowCard className="p-6">
            <div className="mb-5 flex items-center gap-2">
              <Key className="h-4 w-4 text-cyan" />
              <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">
                API Sleutel
              </h2>
            </div>

            <label className={labelCls}>Uw sleutel</label>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <code className="flex-1 select-all rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-neon-green">
                {keyRevealed ? apiKey : maskedKey}
              </code>
              <button
                onClick={() => setKeyRevealed((v) => !v)}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-grid bg-card2 px-4 py-2 text-[12px] text-ink-muted transition-colors hover:border-cyan/40 hover:text-ink"
              >
                {keyRevealed ? (
                  <>
                    <EyeOff className="h-4 w-4" /> Verberg
                  </>
                ) : (
                  <>
                    <Eye className="h-4 w-4" /> Toon sleutel
                  </>
                )}
              </button>
            </div>

            <p className="mt-3 text-[12px] text-ink-muted">
              Gebruik deze sleutel voor programmatische toegang tot CyberPulse.
            </p>

            <div className="mt-6">
              <PrimaryButton
                onClick={() => {
                  if (
                    confirm(
                      "Weet u zeker dat u een nieuwe sleutel wilt genereren? De oude sleutel wordt ongeldig."
                    )
                  ) {
                    toast.success("Nieuwe sleutel gegenereerd");
                  }
                }}
              >
                <RefreshCw className="h-4 w-4" />
                Genereer nieuwe sleutel
              </PrimaryButton>
            </div>
          </GlowCard>
        </motion.div>
      )}

      {/* ── Kali VM ── */}
      {tab === "kali" && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          <GlowCard className="p-6">
            <div className="mb-5 flex items-center gap-2">
              <Server className="h-4 w-4 text-cyan" />
              <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">
                Kali VM
              </h2>
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label className={labelCls}>IP-adres</label>
                <input
                  className={inputCls}
                  value={kaliIp}
                  onChange={(e) => setKaliIp(e.target.value)}
                />
              </div>
              <div>
                <label className={labelCls}>Poort</label>
                <input
                  className={inputCls}
                  value={kaliPort}
                  onChange={(e) => setKaliPort(e.target.value)}
                />
              </div>
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-4">
              <PrimaryButton
                onClick={testConnection}
                disabled={conn === "testing"}
              >
                <Plug className="h-4 w-4" />
                {conn === "testing" ? "Testen..." : "Verbinding testen"}
              </PrimaryButton>

              {conn === "ok" && (
                <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-neon-green">
                  <CheckCircle2 className="h-4 w-4" />
                  Verbonden ✓
                </span>
              )}
              {conn === "fail" && (
                <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-neon-red">
                  <XCircle className="h-4 w-4" />
                  Geen verbinding ✗
                </span>
              )}
            </div>

            {conn === "ok" && toolCount !== null && (
              <p className="mt-3 font-mono text-[12px] text-ink-muted">
                {toolCount} tools gedetecteerd op de Kali VM.
              </p>
            )}

            <p className="mt-5 text-[12px] text-ink-muted">
              Wijzigingen vereisen een herstart van de server.
            </p>
          </GlowCard>
        </motion.div>
      )}
    </div>
  );
}
