"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import {
  Users,
  CreditCard,
  ScanLine,
  Euro,
  Pencil,
  KeyRound,
  Ban,
  CheckCircle,
  Trash2,
  UserPlus,
  Search,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

import { adminApi } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { StatCard } from "@/components/cyber/stat-card";
import { Skeleton } from "@/components/cyber/skeleton";
import { AdminModal } from "@/components/admin/admin-modal";
import {
  Field,
  TextInput,
  Select,
  Toggle,
  Button,
} from "@/components/admin/form-controls";

// ── Constants ────────────────────────────────────────────────────────────────
type TabKey = "overzicht" | "gebruikers" | "scans" | "inkomsten";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overzicht", label: "Overzicht" },
  { key: "gebruikers", label: "Gebruikers" },
  { key: "scans", label: "Scans" },
  { key: "inkomsten", label: "Inkomsten" },
];

const PLANS = ["trial", "starter", "business", "enterprise"] as const;
type Plan = (typeof PLANS)[number];

const PLAN_LABEL: Record<string, string> = {
  trial: "Trial",
  starter: "Starter",
  business: "Business",
  enterprise: "Enterprise",
};

const PLAN_PRICE: Record<string, number> = {
  trial: 0,
  starter: 149,
  business: 349,
  enterprise: 799,
};

const PLAN_COLOR: Record<string, string> = {
  trial: "#4A6880",
  starter: "#00B4D8",
  business: "#0A84FF",
  enterprise: "#00FF88",
};

const INTERVALS = [
  { value: "monthly", label: "Maandelijks" },
  { value: "quarterly", label: "Kwartaal" },
  { value: "yearly", label: "Jaar" },
];

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmtEuro(n: number | undefined | null): string {
  const v = Number(n ?? 0);
  return v.toLocaleString("nl-NL", { maximumFractionDigits: 0 });
}

function fmtDate(d?: string): string {
  if (!d) return "—";
  const date = new Date(d);
  if (isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("nl-NL", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function randomPassword(len = 14): string {
  const chars =
    "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%";
  let out = "";
  const cryptoObj =
    typeof window !== "undefined" ? window.crypto : undefined;
  if (cryptoObj?.getRandomValues) {
    const arr = new Uint32Array(len);
    cryptoObj.getRandomValues(arr);
    for (let i = 0; i < len; i++) out += chars[arr[i] % chars.length];
  } else {
    for (let i = 0; i < len; i++)
      out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function AdminPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<TabKey>("overzicht");

  // `role` is not part of the AuthUser type — read it loosely.
  const role = (user as any)?.role;

  // Guard: non-admins get redirected to the dashboard.
  useEffect(() => {
    if (user && role !== "admin") {
      router.replace("/dashboard");
    }
  }, [user, role, router]);

  // While auth is resolving, show a skeleton.
  if (!user) return <PageSkeleton />;

  // Redirecting — render nothing.
  if (role !== "admin") return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-cyan" />
          <h1 className="font-display text-2xl font-bold text-ink">Beheer</h1>
        </div>
        <p className="font-mono text-[12px] text-ink-muted">
          Gebruikers, abonnementen en omzet beheren
        </p>
      </motion.div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-grid pb-3">
        {TABS.map((t) => {
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`rounded-md px-4 py-2 font-mono text-[12px] uppercase tracking-wider transition-all ${
                active
                  ? "bg-cyan/10 text-cyan shadow-glow-cyan"
                  : "text-ink-muted hover:bg-card2 hover:text-ink"
              }`}
              style={
                active
                  ? { border: "1px solid rgba(0,180,216,0.4)" }
                  : { border: "1px solid transparent" }
              }
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab body */}
      {tab === "overzicht" && <OverviewTab />}
      {tab === "gebruikers" && <UsersTab />}
      {tab === "scans" && <ScansTab />}
      {tab === "inkomsten" && <RevenueTab />}
    </div>
  );
}

// ── Shared: section title ────────────────────────────────────────────────────
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 font-display text-[15px] font-semibold text-ink">
      {children}
    </h2>
  );
}

function Panel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border border-grid bg-card2 ${className}`}>
      {children}
    </div>
  );
}

function ErrorText({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-[#FF2D55]/30 bg-[#FF2D55]/5 px-4 py-3">
      <span className="font-mono text-[12px] text-[#FF2D55]">
        Kon gegevens niet laden.
      </span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-cyan hover:opacity-70"
        >
          <RefreshCw className="h-3 w-3" /> Opnieuw
        </button>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: OVERZICHT
// ═══════════════════════════════════════════════════════════════════════════
function OverviewTab() {
  const [stats, setStats] = useState<any | null>(null);
  const [recentUsers, setRecentUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [statsRes, usersRes] = await Promise.all([
        adminApi.stats(),
        adminApi.users({ sort: "created_at" }),
      ]);
      setStats(statsRes.data);
      const list: any[] = Array.isArray(usersRes.data)
        ? usersRes.data
        : usersRes.data?.users ?? usersRes.data?.items ?? [];
      setRecentUsers(list.slice(0, 10));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[128px] rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-[320px] rounded-lg" />
      </div>
    );
  }

  if (error) return <ErrorText onRetry={load} />;

  const breakdown = stats?.plans_breakdown ?? {};
  const pieData = PLANS.map((p) => ({
    name: PLAN_LABEL[p],
    key: p,
    value: Number(breakdown[p] ?? 0),
  })).filter((d) => d.value > 0);

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Totale gebruikers"
          value={Number(stats?.total_users ?? 0)}
          icon={Users}
          color="#00B4D8"
          index={0}
        />
        <StatCard
          label="Actieve abonnementen"
          value={Number(stats?.active_subscriptions ?? 0)}
          icon={CreditCard}
          color="#0A84FF"
          index={1}
        />
        <StatCard
          label="Scans vandaag"
          value={Number(stats?.total_scans_today ?? 0)}
          icon={ScanLine}
          color="#00FF88"
          index={2}
        />
        <StatCard
          label="Geschatte maandomzet"
          value={Number(stats?.revenue_estimate?.monthly ?? 0)}
          icon={Euro}
          color="#FF8C00"
          index={3}
          suffix="€"
        />
      </div>

      {/* Donut + recent users */}
      <div className="grid gap-4 lg:grid-cols-5">
        {/* Plan breakdown donut */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <SectionTitle>Pakketverdeling</SectionTitle>
          <Panel className="p-4">
            {pieData.length === 0 ? (
              <div className="flex h-[260px] items-center justify-center">
                <span className="font-mono text-[12px] text-ink-muted">
                  Geen gegevens beschikbaar
                </span>
              </div>
            ) : (
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={2}
                      stroke="#080F18"
                      strokeWidth={2}
                    >
                      {pieData.map((d) => (
                        <Cell key={d.key} fill={PLAN_COLOR[d.key]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "#080F18",
                        border: "1px solid #0D1F35",
                        color: "#E8F4F8",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      itemStyle={{ color: "#E8F4F8" }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      iconType="circle"
                      formatter={(value) => (
                        <span
                          style={{
                            color: "#4A6880",
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {value}
                        </span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </Panel>
        </motion.div>

        {/* Recent users */}
        <motion.div
          className="lg:col-span-3"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <SectionTitle>Nieuwste gebruikers</SectionTitle>
          <Panel className="divide-y divide-grid">
            {recentUsers.length === 0 ? (
              <div className="px-4 py-8 text-center font-mono text-[12px] text-ink-muted">
                Nog geen gebruikers.
              </div>
            ) : (
              recentUsers.map((u) => (
                <div
                  key={u.id}
                  className="flex items-center gap-3 px-4 py-3"
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{
                      background: u.is_active === false ? "#FF2D55" : "#00FF88",
                    }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-mono text-[13px] text-ink">
                      {u.name || "—"}
                    </div>
                    <div className="truncate font-mono text-[11px] text-ink-muted">
                      {u.email}
                    </div>
                  </div>
                  <PlanChip plan={u.plan} />
                  <span className="hidden font-mono text-[11px] text-ink-muted sm:inline">
                    {fmtDate(u.created_at)}
                  </span>
                </div>
              ))
            )}
          </Panel>
        </motion.div>
      </div>
    </div>
  );
}

// ── Plan chip ────────────────────────────────────────────────────────────────
function PlanChip({ plan }: { plan?: string }) {
  const key = (plan || "trial").toLowerCase();
  const color = PLAN_COLOR[key] ?? "#4A6880";
  return (
    <span
      className="shrink-0 rounded px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide"
      style={{
        color,
        background: `${color}1A`,
        border: `1px solid ${color}55`,
      }}
    >
      {PLAN_LABEL[key] ?? key}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: GEBRUIKERS
// ═══════════════════════════════════════════════════════════════════════════
function UsersTab() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [planFilter, setPlanFilter] = useState<"all" | Plan>("all");

  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<any | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const params: Record<string, string> = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (planFilter !== "all") params.plan = planFilter;
      const res = await adminApi.users(params);
      const list: any[] = Array.isArray(res.data)
        ? res.data
        : res.data?.users ?? res.data?.items ?? [];
      setUsers(list);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, planFilter]);

  useEffect(() => {
    load();
  }, [load]);

  // ── Row actions ──
  const onResetPassword = async (u: any) => {
    setBusyId(u.id);
    try {
      const res = await adminApi.resetPassword(u.id);
      const temp = res.data?.temp_password ?? res.data?.password;
      if (temp) {
        toast.success(`Tijdelijk wachtwoord voor ${u.email}: ${temp}`, {
          duration: 15000,
        });
      } else {
        toast.success("Wachtwoord opnieuw ingesteld.");
      }
    } catch {
      toast.error("Wachtwoord opnieuw instellen mislukt.");
    } finally {
      setBusyId(null);
    }
  };

  const onToggleActive = async (u: any) => {
    setBusyId(u.id);
    const active = u.is_active !== false;
    try {
      if (active) {
        await adminApi.suspend(u.id);
        toast.success(`${u.email} geblokkeerd.`);
      } else {
        await adminApi.activate(u.id);
        toast.success(`${u.email} geactiveerd.`);
      }
      await load();
    } catch {
      toast.error("Statuswijziging mislukt.");
    } finally {
      setBusyId(null);
    }
  };

  const onDelete = async (u: any) => {
    if (
      !window.confirm(
        `Gebruiker ${u.email} definitief verwijderen? Dit kan niet ongedaan worden gemaakt.`
      )
    )
      return;
    setBusyId(u.id);
    try {
      await adminApi.deleteUser(u.id);
      toast.success(`${u.email} verwijderd.`);
      await load();
    } catch {
      toast.error("Verwijderen mislukt.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Zoek op naam of email…"
            className="w-full rounded-md border border-grid bg-card2 py-2 pl-9 pr-3 font-mono text-[13px] text-ink placeholder:text-ink-muted focus:border-cyan focus:outline-none focus:ring-1 focus:ring-cyan/40"
          />
        </div>
        <Button variant="primary" onClick={() => setCreateOpen(true)}>
          <UserPlus className="h-4 w-4" /> Gebruiker aanmaken
        </Button>
      </div>

      {/* Plan filter pills */}
      <div className="flex flex-wrap gap-2">
        {(["all", ...PLANS] as const).map((p) => {
          const active = planFilter === p;
          const label = p === "all" ? "Alle" : PLAN_LABEL[p];
          return (
            <button
              key={p}
              onClick={() => setPlanFilter(p)}
              className={`rounded-full px-3 py-1 font-mono text-[11px] uppercase tracking-wider transition-all ${
                active
                  ? "bg-cyan/10 text-cyan"
                  : "border border-grid text-ink-muted hover:text-ink"
              }`}
              style={active ? { border: "1px solid rgba(0,180,216,0.4)" } : {}}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-12 rounded-lg" />
          ))}
        </div>
      ) : error ? (
        <ErrorText onRetry={load} />
      ) : users.length === 0 ? (
        <Panel className="px-4 py-10 text-center">
          <span className="font-mono text-[13px] text-ink-muted">
            Geen gebruikers gevonden.
          </span>
        </Panel>
      ) : (
        <Panel className="overflow-x-auto">
          <table className="w-full min-w-[860px] border-collapse">
            <thead>
              <tr className="border-b border-grid text-left">
                {[
                  "Naam",
                  "Email",
                  "Pakket",
                  "Scans/mnd",
                  "Doelen",
                  "Actief",
                  "Aangemaakt",
                  "Acties",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-ink-muted"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const active = u.is_active !== false;
                const isBusy = busyId === u.id;
                return (
                  <tr
                    key={u.id}
                    className="border-b border-grid/60 transition-colors hover:bg-panel/60"
                  >
                    <td className="px-4 py-3 font-mono text-[13px] text-ink">
                      {u.name || "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px] text-ink-muted">
                      {u.email}
                    </td>
                    <td className="px-4 py-3">
                      <PlanChip plan={u.plan} />
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px] tabular-nums text-ink">
                      {u.scans_this_month ?? 0}
                      <span className="text-ink-muted">
                        /{u.max_scans_per_month ?? "∞"}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px] tabular-nums text-ink">
                      {u.max_targets ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center gap-1.5 font-mono text-[11px]"
                        style={{ color: active ? "#00FF88" : "#FF2D55" }}
                      >
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{
                            background: active ? "#00FF88" : "#FF2D55",
                          }}
                        />
                        {active ? "Actief" : "Geblokkeerd"}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-ink-muted">
                      {fmtDate(u.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <IconBtn
                          title="Bewerken"
                          onClick={() => setEditUser(u)}
                          disabled={isBusy}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </IconBtn>
                        <IconBtn
                          title="Wachtwoord opnieuw instellen"
                          onClick={() => onResetPassword(u)}
                          disabled={isBusy}
                        >
                          <KeyRound className="h-3.5 w-3.5" />
                        </IconBtn>
                        <IconBtn
                          title={active ? "Blokkeren" : "Activeren"}
                          onClick={() => onToggleActive(u)}
                          disabled={isBusy}
                          color={active ? "#FF8C00" : "#00FF88"}
                        >
                          {active ? (
                            <Ban className="h-3.5 w-3.5" />
                          ) : (
                            <CheckCircle className="h-3.5 w-3.5" />
                          )}
                        </IconBtn>
                        <IconBtn
                          title="Verwijderen"
                          onClick={() => onDelete(u)}
                          disabled={isBusy}
                          color="#FF2D55"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </IconBtn>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>
      )}

      {/* Modals */}
      <CreateUserModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={() => {
          setCreateOpen(false);
          load();
        }}
      />
      <EditUserModal
        user={editUser}
        onClose={() => setEditUser(null)}
        onSaved={() => {
          setEditUser(null);
          load();
        }}
      />
    </div>
  );
}

function IconBtn({
  children,
  title,
  onClick,
  disabled,
  color = "#4A6880",
}: {
  children: React.ReactNode;
  title: string;
  onClick: () => void;
  disabled?: boolean;
  color?: string;
}) {
  return (
    <button
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
      className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-card2 disabled:cursor-not-allowed disabled:opacity-40"
      style={{ ["--hover" as any]: color }}
      onMouseEnter={(e) => (e.currentTarget.style.color = color)}
      onMouseLeave={(e) => (e.currentTarget.style.color = "")}
    >
      {children}
    </button>
  );
}

// ── Create user modal ────────────────────────────────────────────────────────
function CreateUserModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    company_name: "",
    plan: "trial" as Plan,
    interval: "monthly",
    password: "",
    send_welcome_email: true,
  });
  const [saving, setSaving] = useState(false);

  // Reset form whenever opened.
  useEffect(() => {
    if (open) {
      setForm({
        name: "",
        email: "",
        company_name: "",
        plan: "trial",
        interval: "monthly",
        password: "",
        send_welcome_email: true,
      });
    }
  }, [open]);

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.email.trim()) {
      toast.error("Email is verplicht.");
      return;
    }
    setSaving(true);
    try {
      await adminApi.createUser({
        email: form.email.trim(),
        name: form.name.trim(),
        company_name: form.company_name.trim(),
        plan: form.plan,
        interval: form.interval,
        password: form.password,
        send_welcome_email: form.send_welcome_email,
      });
      toast.success(`Gebruiker ${form.email} aangemaakt.`);
      onCreated();
    } catch (e: any) {
      toast.error(
        e?.response?.data?.detail ?? "Gebruiker aanmaken mislukt."
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <AdminModal
      open={open}
      onClose={onClose}
      title="Gebruiker aanmaken"
      subtitle="Maak een nieuw account aan en wijs een pakket toe"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Annuleren
          </Button>
          <Button variant="primary" onClick={submit} disabled={saving}>
            {saving ? "Bezig…" : "Aanmaken"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Naam">
            <TextInput
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Jan Jansen"
            />
          </Field>
          <Field label="Email">
            <TextInput
              type="email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="jan@bedrijf.nl"
            />
          </Field>
        </div>

        <Field label="Bedrijfsnaam">
          <TextInput
            value={form.company_name}
            onChange={(e) => set("company_name", e.target.value)}
            placeholder="Bedrijf B.V."
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Pakket">
            <Select
              value={form.plan}
              onChange={(e) => set("plan", e.target.value)}
            >
              {PLANS.map((p) => (
                <option key={p} value={p}>
                  {PLAN_LABEL[p]}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Interval">
            <Select
              value={form.interval}
              onChange={(e) => set("interval", e.target.value)}
            >
              {INTERVALS.map((i) => (
                <option key={i.value} value={i.value}>
                  {i.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field label="Tijdelijk wachtwoord">
          <div className="flex gap-2">
            <TextInput
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              placeholder="Leeg = automatisch genereren"
            />
            <Button
              variant="secondary"
              type="button"
              className="shrink-0"
              onClick={() => set("password", randomPassword())}
            >
              <RefreshCw className="h-3.5 w-3.5" /> Genereer
            </Button>
          </div>
        </Field>

        <Toggle
          label="Stuur welkomstmail"
          checked={form.send_welcome_email}
          onChange={(v) => set("send_welcome_email", v)}
        />
      </div>
    </AdminModal>
  );
}

// ── Edit user modal ──────────────────────────────────────────────────────────
function EditUserModal({
  user,
  onClose,
  onSaved,
}: {
  user: any | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setForm({
        plan: user.plan ?? "trial",
        max_targets: user.max_targets ?? 0,
        max_scans_per_month: user.max_scans_per_month ?? 0,
        custom_modules: !!user.custom_modules,
        scheduled_scans: !!user.scheduled_scans,
        white_label: !!user.white_label,
        plan_expires_at: user.plan_expires_at
          ? String(user.plan_expires_at).slice(0, 10)
          : "",
        is_active: user.is_active !== false,
        role: user.role ?? "user",
      });
    } else {
      setForm(null);
    }
  }, [user]);

  const set = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!user || !form) return;
    setSaving(true);
    try {
      await adminApi.updateUser(user.id, {
        plan: form.plan,
        max_targets: Number(form.max_targets),
        max_scans_per_month: Number(form.max_scans_per_month),
        custom_modules: form.custom_modules,
        scheduled_scans: form.scheduled_scans,
        white_label: form.white_label,
        plan_expires_at: form.plan_expires_at || null,
        is_active: form.is_active,
        role: form.role,
      });
      toast.success("Gebruiker bijgewerkt.");
      onSaved();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? "Bijwerken mislukt.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AdminModal
      open={!!user && !!form}
      onClose={onClose}
      title="Gebruiker bewerken"
      subtitle={user?.email}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Annuleren
          </Button>
          <Button variant="primary" onClick={submit} disabled={saving}>
            {saving ? "Bezig…" : "Opslaan"}
          </Button>
        </>
      }
    >
      {form && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Pakket">
              <Select
                value={form.plan}
                onChange={(e) => set("plan", e.target.value)}
              >
                {PLANS.map((p) => (
                  <option key={p} value={p}>
                    {PLAN_LABEL[p]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Rol">
              <Select
                value={form.role}
                onChange={(e) => set("role", e.target.value)}
              >
                <option value="user">Gebruiker</option>
                <option value="admin">Beheerder</option>
              </Select>
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Max. doelen">
              <TextInput
                type="number"
                min={0}
                value={form.max_targets}
                onChange={(e) => set("max_targets", e.target.value)}
              />
            </Field>
            <Field label="Max. scans/mnd">
              <TextInput
                type="number"
                min={0}
                value={form.max_scans_per_month}
                onChange={(e) => set("max_scans_per_month", e.target.value)}
              />
            </Field>
          </div>

          <Field label="Verloopt op">
            <TextInput
              type="date"
              value={form.plan_expires_at}
              onChange={(e) => set("plan_expires_at", e.target.value)}
            />
          </Field>

          <div className="grid gap-2 sm:grid-cols-2">
            <Toggle
              label="Custom modules"
              checked={form.custom_modules}
              onChange={(v) => set("custom_modules", v)}
            />
            <Toggle
              label="Geplande scans"
              checked={form.scheduled_scans}
              onChange={(v) => set("scheduled_scans", v)}
            />
            <Toggle
              label="White-label"
              checked={form.white_label}
              onChange={(v) => set("white_label", v)}
            />
            <Toggle
              label="Account actief"
              checked={form.is_active}
              onChange={(v) => set("is_active", v)}
            />
          </div>
        </div>
      )}
    </AdminModal>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: SCANS (placeholder — no dedicated admin scans endpoint)
// ═══════════════════════════════════════════════════════════════════════════
function ScansTab() {
  return (
    <Panel className="px-6 py-16 text-center">
      <ScanLine className="mx-auto mb-4 h-8 w-8 text-ink-muted" />
      <h3 className="font-display text-[16px] font-semibold text-ink">
        Scans-overzicht komt binnenkort
      </h3>
      <p className="mx-auto mt-2 max-w-md font-mono text-[12px] text-ink-muted">
        Een systeembreed overzicht van alle scans wordt binnenkort toegevoegd.
        Bekijk individuele scans voorlopig via de detailpagina van een
        gebruiker.
      </p>
    </Panel>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TAB: INKOMSTEN
// ═══════════════════════════════════════════════════════════════════════════
function RevenueTab() {
  const [stats, setStats] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await adminApi.stats();
      setStats(res.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const breakdown = stats?.plans_breakdown ?? {};
  const rows = useMemo(
    () =>
      PLANS.map((p) => {
        const count = Number(breakdown[p] ?? 0);
        const price = PLAN_PRICE[p];
        return { plan: p, count, price, total: count * price };
      }),
    [breakdown]
  );
  const computedMonthly = rows.reduce((s, r) => s + r.total, 0);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Skeleton className="h-[128px] rounded-lg" />
          <Skeleton className="h-[128px] rounded-lg" />
        </div>
        <Skeleton className="h-[260px] rounded-lg" />
      </div>
    );
  }

  if (error) return <ErrorText onRetry={load} />;

  const mrr = Number(stats?.revenue_estimate?.monthly ?? computedMonthly);
  const arr = Number(stats?.revenue_estimate?.yearly ?? mrr * 12);

  return (
    <div className="space-y-6">
      {/* MRR / ARR cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <StatCard
          label="MRR — Maandelijkse omzet"
          value={mrr}
          icon={Euro}
          color="#00FF88"
          index={0}
          suffix="€"
        />
        <StatCard
          label="ARR — Jaarlijkse omzet"
          value={arr}
          icon={TrendingUp}
          color="#00B4D8"
          index={1}
          suffix="€"
        />
      </div>

      {/* Breakdown table */}
      <div>
        <SectionTitle>Omzet per pakket</SectionTitle>
        <Panel className="overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse">
            <thead>
              <tr className="border-b border-grid text-left">
                {["Pakket", "Aantal", "Prijs/mnd", "Subtotaal"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 font-mono text-[10px] uppercase tracking-wider text-ink-muted"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.plan} className="border-b border-grid/60">
                  <td className="px-4 py-3">
                    <PlanChip plan={r.plan} />
                  </td>
                  <td className="px-4 py-3 font-mono text-[13px] tabular-nums text-ink">
                    {r.count}
                  </td>
                  <td className="px-4 py-3 font-mono text-[13px] tabular-nums text-ink-muted">
                    €{fmtEuro(r.price)}
                  </td>
                  <td className="px-4 py-3 font-mono text-[13px] font-semibold tabular-nums text-ink">
                    €{fmtEuro(r.total)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-grid">
                <td
                  colSpan={3}
                  className="px-4 py-3 text-right font-mono text-[11px] uppercase tracking-wider text-ink-muted"
                >
                  Totaal MRR
                </td>
                <td className="px-4 py-3 font-mono text-[14px] font-bold tabular-nums text-[#00FF88]">
                  €{fmtEuro(computedMonthly)}
                </td>
              </tr>
            </tfoot>
          </table>
        </Panel>
      </div>
    </div>
  );
}

// ── Full-page loading skeleton (auth resolving) ──────────────────────────────
function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-3 w-64" />
      </div>
      <div className="flex gap-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-9 w-24 rounded-md" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-[128px] rounded-lg" />
        ))}
      </div>
    </div>
  );
}
