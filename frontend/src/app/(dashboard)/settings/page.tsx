"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import Link from "next/link";
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
  Copy,
  LogIn,
  type LucideIcon,
} from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { useAuth } from "@/contexts/auth-context";
import { usersApi } from "@/lib/api";

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

function LoginPrompt({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-start gap-4">
      <p className="text-[13px] text-ink-muted">{message}</p>
      <Link
        href="/login"
        className="inline-flex items-center gap-2 rounded-lg border border-cyan/40 bg-cyan/10 px-4 py-2 text-[13px] font-medium text-cyan transition-all hover:bg-cyan/20 hover:shadow-glow-cyan"
      >
        <LogIn className="h-4 w-4" />
        Inloggen
      </Link>
    </div>
  );
}

export default function SettingsPage() {
  const { user, refresh } = useAuth();
  const [tab, setTab] = useState<TabId>("account");

  // Account
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [savingAccount, setSavingAccount] = useState(false);

  // Notifications
  const [notifyOn, setNotifyOn] = useState(false);
  const [notifyEmail, setNotifyEmail] = useState("");
  const [savingNotify, setSavingNotify] = useState(false);

  // API key
  const [keyRevealed, setKeyRevealed] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  // Kali VM
  const [kaliIp, setKaliIp] = useState("192.168.121.28");
  const [kaliPort, setKaliPort] = useState("5001");
  const [conn, setConn] = useState<"idle" | "testing" | "ok" | "fail">("idle");
  const [responseMs, setResponseMs] = useState<number | null>(null);

  // Prefill form fields from the authenticated user.
  useEffect(() => {
    if (!user) return;
    setName(user.name ?? "");
    setCompany(user.company_name ?? "");
    setNotifyOn(!!user.notify_on_complete);
    setNotifyEmail(user.notification_email ?? "");
  }, [user]);

  // Optional prefill of host/port from backend (graceful — ignore failures).
  useEffect(() => {
    if (tab !== "kali") return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/settings/kali");
        if (!res.ok) return;
        const data: any = await res.json();
        if (cancelled || !data) return;
        const host = data.host ?? data.ip ?? data.kali_ip;
        const port = data.port ?? data.kali_port;
        if (host) setKaliIp(String(host));
        if (port != null) setKaliPort(String(port));
      } catch {
        /* graceful — keep defaults */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tab]);

  async function testConnection() {
    setConn("testing");
    setResponseMs(null);
    try {
      const res = await fetch("/api/settings/kali/test", { method: "POST" });
      if (!res.ok) throw new Error("bad response");
      const data: any = await res.json();
      if (!data?.connected) throw new Error("not connected");
      setResponseMs(
        typeof data.response_time_ms === "number" ? data.response_time_ms : null
      );
      setConn("ok");
    } catch {
      setConn("fail");
    }
  }

  async function saveAccount() {
    setSavingAccount(true);
    try {
      await usersApi.updateMe({ name, company_name: company });
      toast.success("Instellingen opgeslagen");
      await refresh();
    } catch {
      toast.error("Kon instellingen niet opslaan");
    } finally {
      setSavingAccount(false);
    }
  }

  async function saveNotifications() {
    setSavingNotify(true);
    try {
      await usersApi.updateMe({
        notify_on_complete: notifyOn,
        notification_email: notifyEmail,
      });
      toast.success("Instellingen opgeslagen");
      await refresh();
    } catch {
      toast.error("Kon instellingen niet opslaan");
    } finally {
      setSavingNotify(false);
    }
  }

  async function regenerateKey() {
    if (
      !confirm(
        "Weet u zeker dat u een nieuwe sleutel wilt genereren? De oude sleutel wordt ongeldig."
      )
    ) {
      return;
    }
    setRegenerating(true);
    try {
      const res: any = await usersApi.regenerateApiKey();
      const key = res?.data?.api_key ?? res?.data?.key ?? null;
      setNewKey(key);
      toast.success(
        "Nieuwe sleutel gegenereerd — sla deze op, hij wordt niet opnieuw getoond"
      );
      await refresh();
    } catch {
      toast.error("Kon geen nieuwe sleutel genereren");
    } finally {
      setRegenerating(false);
    }
  }

  async function copyKey(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      toast.success("Gekopieerd naar klembord");
    } catch {
      toast.error("Kopiëren mislukt");
    }
  }

  const apiKeyMasked = user?.api_key
    ? `sk-••••${user.api_key.slice(-4)}`
    : "";

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

            {!user ? (
              <LoginPrompt message="Log in om uw account te beheren" />
            ) : (
              <>
                <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                  <div>
                    <label className={labelCls}>Naam</label>
                    <input
                      className={inputCls}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Jan Jansen"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>E-mailadres</label>
                    <input
                      className={`${inputCls} opacity-60`}
                      type="email"
                      value={user.email ?? ""}
                      readOnly
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className={labelCls}>Bedrijfsnaam</label>
                    <input
                      className={inputCls}
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="CyberPulse B.V."
                    />
                  </div>
                </div>
                <div className="mt-6">
                  <PrimaryButton onClick={saveAccount} disabled={savingAccount}>
                    <Save className="h-4 w-4" />
                    {savingAccount ? "Opslaan..." : "Opslaan"}
                  </PrimaryButton>
                </div>
              </>
            )}
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

            {!user ? (
              <LoginPrompt message="Log in om uw notificaties te beheren" />
            ) : (
              <>
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
                    <label className={labelCls}>
                      E-mailadres voor notificaties
                    </label>
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
                  <PrimaryButton onClick={saveNotifications} disabled={savingNotify}>
                    <Save className="h-4 w-4" />
                    {savingNotify ? "Opslaan..." : "Opslaan"}
                  </PrimaryButton>
                </div>
              </>
            )}
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

            {!user ? (
              <LoginPrompt message="Log in om uw API-sleutel te beheren" />
            ) : (
              <>
                <label className={labelCls}>Uw sleutel</label>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <code className="flex-1 select-all rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-neon-green">
                    {user.api_key
                      ? keyRevealed
                        ? user.api_key
                        : apiKeyMasked
                      : "Geen sleutel ingesteld"}
                  </code>
                  {user.api_key && (
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
                  )}
                </div>

                {newKey && (
                  <div className="mt-4 rounded-lg border border-cyan/40 bg-cyan/5 p-4">
                    <p className="mb-2 text-[12px] text-cyan">
                      Nieuwe sleutel — sla deze nu op, hij wordt niet opnieuw
                      getoond:
                    </p>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                      <code className="flex-1 select-all break-all rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-neon-green">
                        {newKey}
                      </code>
                      <button
                        onClick={() => copyKey(newKey)}
                        className="inline-flex items-center justify-center gap-2 rounded-lg border border-grid bg-card2 px-4 py-2 text-[12px] text-ink-muted transition-colors hover:border-cyan/40 hover:text-ink"
                      >
                        <Copy className="h-4 w-4" /> Kopieer
                      </button>
                    </div>
                  </div>
                )}

                <p className="mt-3 text-[12px] text-ink-muted">
                  Gebruik deze sleutel voor programmatische toegang tot
                  CyberPulse.
                </p>

                <div className="mt-6">
                  <PrimaryButton onClick={regenerateKey} disabled={regenerating}>
                    <RefreshCw className="h-4 w-4" />
                    {regenerating ? "Genereren..." : "Genereer nieuwe sleutel"}
                  </PrimaryButton>
                </div>
              </>
            )}
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
                  {responseMs !== null
                    ? `Verbonden — ${responseMs}ms reactietijd`
                    : "Verbonden"}
                </span>
              )}
              {conn === "fail" && (
                <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-neon-red">
                  <XCircle className="h-4 w-4" />
                  Geen verbinding — controleer IP en poort
                </span>
              )}
            </div>

            <div className="mt-6">
              <PrimaryButton
                onClick={() => toast.success("Instellingen opgeslagen")}
              >
                <Save className="h-4 w-4" />
                Opslaan
              </PrimaryButton>
            </div>

            <p className="mt-5 text-[12px] text-ink-muted">
              Wijzigingen vereisen een herstart van de server.
            </p>
          </GlowCard>
        </motion.div>
      )}
    </div>
  );
}
