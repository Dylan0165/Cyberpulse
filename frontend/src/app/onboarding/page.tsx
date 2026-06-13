"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Shield, Check, ArrowRight, Loader2, Clock } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { authApi, targetsApi, scansApi } from "@/lib/api";

const IP_REGEX =
  /^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$/;
const DOMAIN_REGEX =
  /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;

function isValidTarget(value: string): boolean {
  const v = value.trim();
  return IP_REGEX.test(v) || DOMAIN_REGEX.test(v);
}

export default function OnboardingPage() {
  const router = useRouter();
  const { user } = useAuth();

  const [step, setStep] = useState<1 | 2>(1);
  const [name, setName] = useState("");
  const [ip, setIp] = useState("");
  const [busy, setBusy] = useState(false);

  const ipValid = useMemo(() => isValidTarget(ip), [ip]);
  const nameValid = name.trim().length > 0;
  const step1Valid = nameValid && ipValid;

  const greetingName = user?.name ?? "daar";

  async function startScan() {
    if (busy) return;
    setBusy(true);
    try {
      const targetRes: any = await targetsApi.create({
        value: ip.trim(),
        name: name.trim(),
        target_type: "url",
        hostname: ip.trim(),
      });
      const scanRes: any = await scansApi.create({
        target_id: targetRes.data.id,
        scan_type: "full",
        phases: ["recon", "vulnerability", "ssl"],
        scan_mode: "blackbox",
        target_type: "web",
      });
      try {
        await authApi.completeOnboarding();
      } catch {
        /* best-effort */
      }
      router.push(`/scans/${scanRes.data.id}`);
    } catch {
      toast.error("Kon scan niet starten");
      setBusy(false);
    }
  }

  async function skip() {
    if (busy) return;
    setBusy(true);
    try {
      await authApi.completeOnboarding();
    } catch {
      /* best-effort */
    }
    router.push("/dashboard");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-app px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Progress dots */}
        <div className="mb-10 flex items-center justify-center gap-0">
          <Dot active={step >= 1} done={step > 1} index={1} />
          <div
            className="h-[2px] w-16 transition-colors duration-300"
            style={{ background: step > 1 ? "#00D4FF" : "var(--border)" }}
          />
          <Dot active={step >= 2} done={false} index={2} />
        </div>

        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-grid bg-card2 shadow-glow-cyan">
            <Shield className="h-6 w-6 text-cyan" />
          </div>
        </div>

        {step === 1 ? (
          <motion.div
            key="step1"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-xl border border-grid bg-panel p-6 shadow-glow-cyan"
          >
            <h1 className="font-display text-2xl font-bold text-ink">
              Welkom bij CyberPulse, {greetingName}
            </h1>
            <p className="mt-1 text-sm text-ink-muted">
              Laten we uw eerste systeem instellen
            </p>

            <label className="mt-6 mb-4 block">
              <span className="mb-1.5 block text-sm font-medium text-ink-muted">
                Naam
              </span>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="bijv. Onze website"
                className="w-full rounded-lg border border-grid bg-card2 px-3 py-2.5 text-ink outline-none transition-colors focus:border-cyan"
              />
            </label>

            <label className="mb-6 block">
              <span className="mb-1.5 block text-sm font-medium text-ink-muted">
                IP of domein
              </span>
              <input
                type="text"
                value={ip}
                onChange={(e) => setIp(e.target.value)}
                placeholder="bijv. uwbedrijf.nl of 192.168.1.1"
                className="w-full rounded-lg border border-grid bg-card2 px-3 py-2.5 text-ink outline-none transition-colors focus:border-cyan"
                style={
                  ip.length > 0
                    ? { borderColor: ipValid ? "#00FF88" : "#FF2D55" }
                    : undefined
                }
              />
              {ip.length > 0 && !ipValid && (
                <span className="mt-1 block text-xs text-neon-red">
                  Voer een geldig IP-adres of domein in
                </span>
              )}
            </label>

            <button
              type="button"
              disabled={!step1Valid}
              onClick={() => setStep(2)}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-semibold text-app shadow-glow-cyan transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Volgende <ArrowRight className="h-4 w-4" />
            </button>
          </motion.div>
        ) : (
          <motion.div
            key="step2"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-xl border border-grid bg-panel p-6 shadow-glow-cyan"
          >
            <h1 className="font-display text-2xl font-bold text-ink">
              Wilt u nu uw eerste scan starten?
            </h1>

            <div className="mt-6 rounded-lg border border-grid bg-card2 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-ink-muted">Systeem</span>
                <span className="font-medium text-ink">{name.trim()}</span>
              </div>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-sm text-ink-muted">Doel</span>
                <span className="font-mono text-sm text-cyan">{ip.trim()}</span>
              </div>
              <div className="mt-3 flex items-center gap-1.5 text-sm text-ink-muted">
                <Clock className="h-4 w-4" />
                <span>~5 minuten</span>
              </div>
            </div>

            <button
              type="button"
              disabled={busy}
              onClick={startScan}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-semibold text-app shadow-glow-cyan transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Scan starten <ArrowRight className="h-4 w-4" />
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={skip}
              className="mt-3 w-full rounded-lg px-4 py-2.5 text-sm text-ink-muted transition-colors hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
            >
              Dit overslaan
            </button>

            <button
              type="button"
              disabled={busy}
              onClick={() => setStep(1)}
              className="mt-1 w-full text-center text-xs text-ink-muted transition-colors hover:text-cyan disabled:opacity-60"
            >
              &larr; Terug
            </button>
          </motion.div>
        )}
      </div>
    </main>
  );
}

function Dot({
  active,
  done,
  index,
}: {
  active: boolean;
  done: boolean;
  index: number;
}) {
  return (
    <div
      className="flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors duration-300"
      style={{
        borderColor: active ? "#00D4FF" : "var(--border)",
        background: active ? "rgba(0,212,255,0.1)" : "transparent",
        color: active ? "#00D4FF" : "var(--text-muted)",
      }}
    >
      {done ? <Check className="h-4 w-4" /> : index}
    </div>
  );
}
