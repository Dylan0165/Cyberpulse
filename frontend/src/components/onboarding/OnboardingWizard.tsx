"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Radar, ArrowRight, ArrowLeft, Check, Loader2, Target as TargetIcon } from "lucide-react";
import { usersApi, targetsApi } from "@/lib/api";

const ONB_KEY = "scanix_onboarding_done";

function detectType(v: string): "ip" | "network" | "web" {
  const s = v.trim();
  if (/\/\d{1,2}$/.test(s)) return "network";
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(s)) return "ip";
  return "web";
}
const TYPE_LABEL = { ip: "Server", network: "Subnet", web: "Website" } as const;

function Dots({ active }: { active: number }) {
  return (
    <div className="mt-6 flex items-center justify-center gap-2">
      {[0, 1, 2].map((i) => (
        <span key={i} className={`h-1.5 rounded-full transition-all ${i === active ? "w-8 bg-cyan" : "w-2 bg-grid"}`} />
      ))}
    </div>
  );
}

/**
 * One-time 3-step onboarding overlay. Visibility is decided by the parent
 * (renders only when user.onboarding_completed === false). On finish it calls
 * the backend + sets the localStorage fallback so it never shows again.
 */
export function OnboardingWizard() {
  const router = useRouter();
  const [open, setOpen] = useState(true);
  const [step, setStep] = useState(0);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [createdTargetId, setCreatedTargetId] = useState<string | null>(null);

  if (!open) return null;

  const invalid =
    !value.trim() || /localhost/i.test(value) || /^127\./.test(value.trim()) || /^0\.0\.0\.0/.test(value.trim());

  const complete = async (then?: () => void) => {
    try {
      await usersApi.completeOnboarding();
    } catch {
      /* non-fatal */
    }
    if (typeof window !== "undefined") localStorage.setItem(ONB_KEY, "true");
    setOpen(false);
    then?.();
  };

  const addTargetAndNext = async () => {
    if (invalid) {
      toast.error("Voer een geldig domein of IP in (geen localhost / 127.x).");
      return;
    }
    setBusy(true);
    try {
      const res = await targetsApi.create({
        value: value.trim(),
        name: value.trim(),
        target_type: detectType(value),
      });
      setCreatedTargetId(res.data?.id ?? null);
      setStep(2);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      toast.error(detail && typeof detail === "object" && detail.message ? detail.message : "Doel toevoegen mislukt.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-grid bg-card2 shadow-glow-cyan">
        {step < 2 && (
          <button
            type="button"
            onClick={() => (step === 1 ? complete(() => router.push("/dashboard")) : complete())}
            className="absolute right-4 top-4 z-10 font-mono text-[11px] text-ink-muted transition-colors hover:text-ink"
          >
            Overslaan
          </button>
        )}

        <div className="p-8">
          {/* STEP 1 — Welcome */}
          {step === 0 && (
            <div className="text-center">
              <div className="relative mx-auto mb-6 flex h-20 w-20 items-center justify-center">
                <span className="onb-pulse absolute inset-0 rounded-full border border-cyan/60" />
                <span className="onb-pulse onb-pulse-2 absolute inset-0 rounded-full border border-cyan/40" />
                <span className="relative flex h-16 w-16 items-center justify-center rounded-full border border-cyan/40 bg-cyan/10">
                  <Radar className="h-8 w-8 text-cyan" />
                </span>
              </div>
              <h2 className="font-display text-2xl font-bold text-ink">Welkom bij Scanix</h2>
              <p className="mt-1 font-mono text-[12px] uppercase tracking-[0.16em] text-cyan">Uw digitale beveiligingspartner</p>
              <p className="mt-4 text-[14px] leading-relaxed text-ink-muted">
                In 3 stappen start u uw eerste beveiligingsscan. Uw gratis trial credit staat al klaar.
              </p>
              <Dots active={0} />
              <button
                type="button"
                onClick={() => setStep(1)}
                className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[13px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform hover:scale-[1.01] active:scale-[0.99]"
              >
                Aan de slag <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* STEP 2 — Target */}
          {step === 1 && (
            <div>
              <h2 className="font-display text-xl font-bold text-ink">Voeg uw eerste systeem toe</h2>
              <p className="mt-2 text-[13px] text-ink-muted">Vul een domein of IP-adres in dat u wilt laten testen.</p>
              <input
                autoFocus
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !invalid && !busy && addTargetAndNext()}
                placeholder="bedrijf.nl of 1.2.3.4"
                className="mt-4 w-full rounded-lg border border-grid bg-app px-4 py-3 font-mono text-[14px] text-ink outline-none focus:border-cyan/60"
              />
              {value.trim() && (
                <span className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-grid bg-app px-3 py-1 font-mono text-[11px] text-cyan">
                  <TargetIcon className="h-3.5 w-3.5" /> {TYPE_LABEL[detectType(value)]}
                </span>
              )}
              <Dots active={1} />
              <div className="mt-6 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setStep(0)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-grid bg-app px-4 py-2.5 font-mono text-[12px] text-ink-muted hover:text-ink"
                >
                  <ArrowLeft className="h-4 w-4" /> Vorige
                </button>
                <button type="button" onClick={() => setStep(2)} className="rounded-lg px-3 py-2.5 font-mono text-[12px] text-ink-muted hover:text-ink">
                  Sla over, doe dit later
                </button>
                <button
                  type="button"
                  onClick={addTargetAndNext}
                  disabled={invalid || busy}
                  className="ml-auto inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-display text-[12px] font-bold uppercase tracking-[0.1em] text-app disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Volgende <ArrowRight className="h-4 w-4" /></>}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3 — Done */}
          {step === 2 && (
            <div className="text-center">
              {createdTargetId ? (
                <>
                  <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-neon-green/40 bg-neon-green/10">
                    <Check className="h-7 w-7 text-neon-green" />
                  </div>
                  <p className="font-mono text-[12px] uppercase tracking-[0.14em] text-neon-green">Target toegevoegd</p>
                  <h2 className="mt-2 font-display text-xl font-bold text-ink">U bent klaar om te starten</h2>
                  <p className="mt-2 text-[13px] text-ink-muted">Klik hieronder om uw eerste gratis scan te starten.</p>
                  <Dots active={2} />
                  <button
                    type="button"
                    onClick={() => complete(() => router.push(`/scans/new?target=${createdTargetId}`))}
                    className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[13px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform hover:scale-[1.01]"
                  >
                    Start mijn gratis scan <ArrowRight className="h-4 w-4" />
                  </button>
                </>
              ) : (
                <>
                  <h2 className="font-display text-xl font-bold text-ink">Uw dashboard staat klaar</h2>
                  <p className="mt-2 text-[13px] text-ink-muted">Voeg een target toe om uw eerste scan te starten.</p>
                  <Dots active={2} />
                  <button
                    type="button"
                    onClick={() => complete(() => router.push("/dashboard"))}
                    className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[13px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan transition-transform hover:scale-[1.01]"
                  >
                    Naar dashboard <ArrowRight className="h-4 w-4" />
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .onb-pulse { animation: onb-pulse 2s ease-out infinite; }
        .onb-pulse-2 { animation-delay: 1s; }
        @keyframes onb-pulse {
          0%   { transform: scale(0.6); opacity: 0.8; }
          100% { transform: scale(1.4); opacity: 0; }
        }
        @media (prefers-reduced-motion: reduce) { .onb-pulse { animation: none; opacity: 0; } }
      `}</style>
    </div>
  );
}

export default OnboardingWizard;
