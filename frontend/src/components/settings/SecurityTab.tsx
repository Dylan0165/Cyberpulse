"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ShieldCheck, KeyRound, Users, Copy, Check, Loader2, Trash2, Plus } from "lucide-react";
import { GlowCard } from "@/components/cyber/glow-card";
import { authApi, accessKeysApi, teamApi } from "@/lib/api";

const SCOPES = ["scan:read", "scan:create", "scan:delete", "report:read", "target:manage"];
const ROLES = ["viewer", "analyst", "admin"];

export function SecurityTab() {
  // ── 2FA ──
  const [twofaEnabled, setTwofaEnabled] = useState<boolean | null>(null);
  const [setup, setSetup] = useState<{ secret: string; qr_uri: string; backup_codes: string[] } | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [disablePw, setDisablePw] = useState("");

  useEffect(() => {
    authApi.twofaStatus().then((r) => setTwofaEnabled(r.data.enabled)).catch(() => setTwofaEnabled(false));
  }, []);

  const startSetup = async () => {
    setBusy(true);
    try {
      const { data } = await authApi.twofaSetup();
      setSetup(data);
    } catch {
      toast.error("2FA-setup mislukt.");
    } finally {
      setBusy(false);
    }
  };
  const confirmSetup = async () => {
    setBusy(true);
    try {
      await authApi.twofaVerifySetup(code);
      setTwofaEnabled(true);
      toast.success("2FA geactiveerd");
    } catch {
      toast.error("Ongeldige code.");
    } finally {
      setBusy(false);
    }
  };
  const disable2fa = async () => {
    setBusy(true);
    try {
      await authApi.twofaDisable(code, disablePw);
      setTwofaEnabled(false);
      setSetup(null);
      setCode("");
      setDisablePw("");
      toast.success("2FA uitgeschakeld");
    } catch {
      toast.error("Uitschakelen mislukt (controleer wachtwoord en code).");
    } finally {
      setBusy(false);
    }
  };

  // ── API keys ──
  const [keys, setKeys] = useState<any[]>([]);
  const [keyName, setKeyName] = useState("");
  const [keyScopes, setKeyScopes] = useState<string[]>(["scan:read", "scan:create"]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const loadKeys = () => accessKeysApi.list().then((r) => setKeys(r.data)).catch(() => setKeys([]));
  useEffect(() => { loadKeys(); }, []);
  const createKey = async () => {
    if (!keyName.trim()) return;
    try {
      const { data } = await accessKeysApi.create({ name: keyName.trim(), scopes: keyScopes });
      setNewKey(data.key);
      setKeyName("");
      loadKeys();
    } catch {
      toast.error("API key aanmaken mislukt.");
    }
  };

  // ── Team ──
  const [members, setMembers] = useState<any[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const loadMembers = () => teamApi.members().then((r) => setMembers(r.data)).catch(() => setMembers([]));
  useEffect(() => { loadMembers(); }, []);
  const invite = async () => {
    if (!inviteEmail.trim()) return;
    try {
      await teamApi.invite(inviteEmail.trim(), inviteRole);
      toast.success("Uitnodiging verstuurd");
      setInviteEmail("");
      loadMembers();
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      toast.error(d && typeof d === "object" && d.message ? d.message : "Uitnodigen mislukt.");
    }
  };

  return (
    <div className="space-y-5">
      {/* 2FA */}
      <GlowCard className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-cyan" />
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">Twee-factor authenticatie</h2>
          {twofaEnabled && <span className="ml-auto rounded-full border border-neon-green/50 bg-neon-green/10 px-2 py-0.5 font-mono text-[10px] text-neon-green">2FA actief</span>}
        </div>

        {twofaEnabled ? (
          <div className="space-y-3">
            <p className="text-[12px] text-ink-muted">2FA is ingeschakeld. Uitschakelen vereist uw wachtwoord en een geldige code.</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <input value={disablePw} onChange={(e) => setDisablePw(e.target.value)} type="password" placeholder="Wachtwoord" className="rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-ink outline-none focus:border-cyan/60" />
              <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="123456" className="rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-ink outline-none focus:border-cyan/60" />
            </div>
            <button onClick={disable2fa} disabled={busy} className="rounded-lg border border-neon-red/50 bg-neon-red/10 px-4 py-2 font-mono text-[12px] text-neon-red disabled:opacity-50">2FA uitschakelen</button>
          </div>
        ) : !setup ? (
          <button onClick={startSetup} disabled={busy} className="inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "2FA inschakelen"}
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-[12px] text-ink-muted">Voeg dit toe in Google Authenticator of Authy. Scan een QR of voer de sleutel handmatig in:</p>
            <div className="rounded-lg border border-grid bg-app p-3 font-mono text-[12px] text-cyan break-all">{setup.secret}</div>
            <p className="text-[11px] text-ink-muted break-all">otpauth: {setup.qr_uri}</p>
            <div className="rounded-lg border border-grid bg-app p-3">
              <p className="mb-1 font-mono text-[10px] uppercase tracking-wider text-ink-muted">Herstelcodes (bewaar veilig, elk eenmalig)</p>
              <div className="grid grid-cols-2 gap-1 font-mono text-[12px] text-ink sm:grid-cols-4">
                {setup.backup_codes.map((c) => <span key={c}>{c}</span>)}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="123456" className="flex-1 rounded-lg border border-grid bg-app px-3 py-2 text-center font-mono text-[15px] tracking-[0.3em] text-ink outline-none focus:border-cyan/60" />
              <button onClick={confirmSetup} disabled={busy || code.length !== 6} className="rounded-lg bg-cyan px-4 py-2 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app disabled:opacity-50">Activeer</button>
            </div>
          </div>
        )}
      </GlowCard>

      {/* API keys */}
      <GlowCard className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-cyan" />
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">API keys</h2>
        </div>
        {newKey && (
          <div className="mb-4 rounded-lg border border-cyan/40 bg-cyan/10 p-3">
            <p className="mb-1 font-mono text-[11px] text-cyan">Bewaar deze key — u ziet hem niet terug.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all font-mono text-[12px] text-ink">{newKey}</code>
              <button onClick={async () => { try { await navigator.clipboard.writeText(newKey); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {} }} className="rounded border border-grid px-2 py-1 text-ink-muted hover:text-cyan">
                {copied ? <Check className="h-3.5 w-3.5 text-neon-green" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
        )}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <input value={keyName} onChange={(e) => setKeyName(e.target.value)} placeholder="Naam (bv. CI/CD Pipeline)" className="flex-1 rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-ink outline-none focus:border-cyan/60" />
          <button onClick={createKey} disabled={!keyName.trim()} className="inline-flex items-center gap-1.5 rounded-lg bg-cyan px-3 py-2 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app disabled:opacity-50"><Plus className="h-4 w-4" /> Aanmaken</button>
        </div>
        <div className="mb-3 flex flex-wrap gap-1.5">
          {SCOPES.map((s) => {
            const on = keyScopes.includes(s);
            return (
              <button key={s} onClick={() => setKeyScopes((p) => on ? p.filter((x) => x !== s) : [...p, s])} className={`rounded-md border px-2 py-1 font-mono text-[10px] ${on ? "border-cyan/60 bg-cyan/10 text-cyan" : "border-grid text-ink-muted"}`}>{s}</button>
            );
          })}
        </div>
        <div className="space-y-2">
          {keys.length === 0 ? (
            <p className="font-mono text-[12px] text-ink-muted">Nog geen API keys.</p>
          ) : keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between rounded-lg border border-grid bg-app px-3 py-2">
              <div>
                <span className="font-mono text-[12px] text-ink">{k.name}</span>
                <span className="ml-2 font-mono text-[11px] text-ink-muted">{k.prefix}…</span>
                <div className="font-mono text-[10px] text-ink-muted">{(k.scopes || []).join(", ")}</div>
              </div>
              <button onClick={async () => { await accessKeysApi.remove(k.id); loadKeys(); }} className="rounded border border-grid p-1.5 text-ink-muted hover:border-neon-red/50 hover:text-neon-red"><Trash2 className="h-3.5 w-3.5" /></button>
            </div>
          ))}
        </div>
      </GlowCard>

      {/* Team */}
      <GlowCard className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <Users className="h-4 w-4 text-cyan" />
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink">Teamleden</h2>
        </div>
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="collega@bedrijf.nl" className="flex-1 rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[13px] text-ink outline-none focus:border-cyan/60" />
          <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className="rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[12px] text-ink">
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <button onClick={invite} disabled={!inviteEmail.trim()} className="rounded-lg bg-cyan px-3 py-2 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app disabled:opacity-50">Uitnodigen</button>
        </div>
        <div className="space-y-2">
          {members.length === 0 ? (
            <p className="font-mono text-[12px] text-ink-muted">Nog geen teamleden. Beschikbaar vanaf het Business-pakket.</p>
          ) : members.map((m) => (
            <div key={m.id} className="flex items-center justify-between rounded-lg border border-grid bg-app px-3 py-2 font-mono text-[12px]">
              <span className="text-ink">{m.email}</span>
              <span className="text-ink-muted">{m.role} · {m.status}</span>
              <button onClick={async () => { await teamApi.remove(m.id); loadMembers(); }} className="rounded border border-grid p-1.5 text-ink-muted hover:border-neon-red/50 hover:text-neon-red"><Trash2 className="h-3.5 w-3.5" /></button>
            </div>
          ))}
        </div>
      </GlowCard>
    </div>
  );
}

export default SecurityTab;
