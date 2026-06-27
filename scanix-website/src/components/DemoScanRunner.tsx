"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Play, Loader2, Lock, ArrowRight, ShieldCheck } from "lucide-react";

// App API base — configurable so it works in any environment (no hard-coded domain).
// Domain-free default (test/netlab IP); set NEXT_PUBLIC_APP_API_URL in production.
const API = (process.env.NEXT_PUBLIC_APP_API_URL || "http://192.168.121.40").replace(/\/$/, "");
const REGISTER_URL = `${API.replace("/api", "")}/register`;

type DemoState = {
  id: string;
  status: string;
  target: string;
  terminal_output: string;
  findings: { title?: string; severity?: string; description?: string }[];
  total_findings: number;
  locked_findings: number;
};

export function DemoScanRunner() {
  const t = useTranslations("demoPage");
  const [state, setState] = useState<DemoState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const start = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/demo/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (res.status === 429) {
        setError(t("rateLimit"));
        setBusy(false);
        return;
      }
      if (!res.ok) throw new Error("start failed");
      const data = await res.json();
      const id = data.demo_scan_id;
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${API}/api/demo/${id}`);
          if (!r.ok) return;
          const d: DemoState = await r.json();
          setState(d);
          if (d.status === "completed" || d.status === "failed") {
            if (pollRef.current) clearInterval(pollRef.current);
            setBusy(false);
          }
        } catch { /* keep polling */ }
      }, 3000);
    } catch {
      setError(t("error"));
      setBusy(false);
    }
  };

  const sevColor = (s?: string) =>
    s === "CRITICAL" ? "text-red-400" : s === "HIGH" ? "text-orange-400" : s === "MEDIUM" ? "text-amber-400" : "text-ink-muted";

  return (
    <div className="mx-auto max-w-3xl">
      {!state && (
        <div className="text-center">
          <button
            type="button"
            onClick={start}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan px-7 py-4 text-[15px] font-bold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98] disabled:opacity-60"
          >
            {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
            {t("startButton")}
          </button>
          <p className="mt-3 font-mono text-[12px] text-ink-muted">⚡ {t("duration")}</p>
          {error && <p className="mt-3 font-mono text-[12px] text-red-400">{error}</p>}
        </div>
      )}

      {state && (
        <div className="space-y-5">
          {/* Live terminal */}
          <div className="overflow-hidden rounded-xl border border-grid bg-black">
            <div className="flex items-center gap-2 border-b border-grid px-4 py-2 font-mono text-[11px] text-ink-muted">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
              <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
              <span className="ml-2">scanix@demo — {state.target}</span>
              {state.status === "running" && <Loader2 className="ml-auto h-3.5 w-3.5 animate-spin text-cyan" />}
            </div>
            <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap p-4 font-mono text-[12px] leading-relaxed text-green-400">
              {state.terminal_output || t("running")}
            </pre>
          </div>

          {/* Findings */}
          {state.findings.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-display text-lg font-bold text-ink">{t("findingsTitle")}</h3>
              {state.findings.map((f, i) => (
                <div key={i} className="rounded-lg border border-grid bg-card p-3">
                  <span className={`font-mono text-[11px] font-bold ${sevColor(f.severity)}`}>{f.severity}</span>
                  <span className="ml-2 text-[13px] text-ink">{f.title}</span>
                </div>
              ))}
              {state.locked_findings > 0 && (
                <div className="relative overflow-hidden rounded-lg border border-grid bg-card p-6 text-center">
                  <div className="pointer-events-none absolute inset-0 backdrop-blur-sm" />
                  <div className="relative">
                    <Lock className="mx-auto mb-2 h-6 w-6 text-cyan" />
                    <p className="text-[14px] text-ink">{t("lockedMore", { count: state.locked_findings })}</p>
                    <a href={REGISTER_URL} className="mt-3 inline-flex items-center gap-2 rounded-lg bg-cyan px-5 py-2.5 text-[13px] font-semibold text-bg">
                      {t("createAccount")} <ArrowRight className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}

          {state.status === "completed" && state.findings.length > 0 && (
            <div className="flex items-center justify-center gap-2 font-mono text-[13px] text-green-400">
              <ShieldCheck className="h-4 w-4" /> {t("done")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DemoScanRunner;
