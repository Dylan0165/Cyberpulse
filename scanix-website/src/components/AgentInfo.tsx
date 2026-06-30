"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ShieldOff, ServerCog, RefreshCw, Copy, Check, ArrowRight } from "lucide-react";
import { APP_URL } from "@/lib/appUrl";

const INSTALL_CMD =
  `curl -sSL ${APP_URL}/agent/install.sh | SCANIX_URL=${APP_URL} AGENT_TOKEN=UW_TOKEN bash`;
const APP_AGENTS = `${APP_URL}/agents`;

export function AgentInfo() {
  const t = useTranslations("agentPage");
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(INSTALL_CMD);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — non-fatal */
    }
  };

  const benefits = [
    { icon: ShieldOff, title: t("benefitTitle"), text: t("benefitText") },
    { icon: ServerCog, title: t("benefit2Title"), text: t("benefit2Text") },
    { icon: RefreshCw, title: t("benefit3Title"), text: t("benefit3Text") },
  ];

  const steps = [
    { title: t("step1Title"), text: t("step1Text") },
    { title: t("step2Title"), text: t("step2Text") },
    { title: t("step3Title"), text: t("step3Text") },
  ];

  return (
    <section className="relative mx-auto max-w-content px-5 py-12 md:px-8 md:py-16">
      <p className="mx-auto max-w-2xl text-center text-[16px] leading-relaxed text-ink-muted">
        {t("intro")}
      </p>

      {/* Benefits */}
      <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
        {benefits.map((b) => (
          <div key={b.title} className="rounded-2xl border border-grid bg-card p-6">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-cyan/30 bg-cyan/10">
              <b.icon className="h-5 w-5 text-cyan" strokeWidth={2} />
            </span>
            <h3 className="mt-4 font-display text-lg font-bold tracking-tight text-ink">{b.title}</h3>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">{b.text}</p>
          </div>
        ))}
      </div>

      {/* Steps */}
      <div className="mx-auto mt-16 max-w-3xl">
        <h2 className="text-center font-display text-2xl font-bold tracking-tight text-ink">
          {t("stepsTitle")}
        </h2>
        <ol className="mt-8 space-y-4">
          {steps.map((s, i) => (
            <li key={s.title} className="flex gap-4 rounded-2xl border border-grid bg-card p-5">
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-cyan/15 font-mono text-[14px] font-bold text-cyan">
                {i + 1}
              </span>
              <div>
                <h3 className="font-display text-[16px] font-semibold text-ink">{s.title}</h3>
                <p className="mt-1 text-[14px] leading-relaxed text-ink-muted">{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Linux install */}
      <div className="mx-auto mt-12 max-w-3xl">
        <h3 className="font-display text-lg font-bold text-ink">{t("linuxTitle")}</h3>
        <div className="mt-3 flex items-center gap-3 overflow-x-auto rounded-xl border border-grid bg-bg p-4">
          <code className="flex-1 whitespace-pre font-mono text-[13px] text-cyan">{INSTALL_CMD}</code>
          <button
            type="button"
            onClick={copy}
            aria-label="Copy"
            className="inline-flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-grid px-3 py-1.5 font-mono text-[12px] text-ink-muted transition-colors hover:border-cyan/40 hover:text-cyan"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
        <p className="mt-2 text-[12px] text-ink-muted">{t("tokenNote")}</p>

        <h3 className="mt-8 flex items-center gap-2 font-display text-lg font-bold text-ink">
          {t("windowsTitle")}
          <span className="rounded-full border border-grid px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-ink-muted">
            {t("windowsSoon")}
          </span>
        </h3>

        <div className="mt-8 flex justify-center">
          <a
            href={APP_AGENTS}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan px-6 py-3 text-[14px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98]"
          >
            {t("ctaDashboard")} <ArrowRight className="h-4 w-4" strokeWidth={2} />
          </a>
        </div>
      </div>
    </section>
  );
}
