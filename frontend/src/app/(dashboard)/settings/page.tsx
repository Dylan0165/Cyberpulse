"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import Link from "next/link";
import { User, Bell, Save, LogIn, type LucideIcon } from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { useAuth } from "@/contexts/auth-context";
import { usersApi } from "@/lib/api";

type TabId = "account" | "notifications";

const TABS: { id: TabId; label: string; icon: LucideIcon }[] = [
  { id: "account", label: "Account", icon: User },
  { id: "notifications", label: "Notificaties", icon: Bell },
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

  // Prefill form fields from the authenticated user.
  useEffect(() => {
    if (!user) return;
    setName(user.name ?? "");
    setCompany(user.company_name ?? "");
    setNotifyOn(!!user.notify_on_complete);
    setNotifyEmail(user.notification_email ?? "");
  }, [user]);

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

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold tracking-[0.02em] text-ink">
          Instellingen
        </h1>
        <p className="mt-1 text-[13px] text-ink-muted">
          Beheer uw account en meldingen
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
                      placeholder="Scanix B.V."
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
                      notifyOn ? "border-cyan bg-cyan/30" : "border-grid bg-card2"
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
    </div>
  );
}
