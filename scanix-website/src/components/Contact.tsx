"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Clock, BarChart3, Wallet, RefreshCw, Check, Loader2, AlertCircle } from "lucide-react";

type Status = "idle" | "sending" | "success" | "error";

const labelCls = "mb-1.5 block text-[12px] font-medium text-ink-muted";
const inputCls =
  "w-full rounded-lg border border-grid bg-bg-secondary px-3.5 py-2.5 text-[14px] text-ink placeholder:text-ink-muted/50 outline-none transition-colors focus:border-cyan";

export function Contact() {
  const t = useTranslations("contact");
  const [status, setStatus] = useState<Status>("idle");
  const [consent, setConsent] = useState(false);
  const [showErr, setShowErr] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries());

    if (!data.name || !data.company || !data.email || !data.target || !consent) {
      setShowErr(true);
      return;
    }
    setShowErr(false);
    setStatus("sending");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error("bad response");
      setStatus("success");
      form.reset();
      setConsent(false);
    } catch {
      setStatus("error");
    }
  }

  const stats = [
    { icon: Clock, text: t("statDuration") },
    { icon: BarChart3, text: t("statFindings") },
    { icon: Wallet, text: t("statCheaper") },
    { icon: RefreshCw, text: t("statFrequency") },
  ];

  return (
    <section id="contact" className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      <div className="glow-accent right-[-5%] top-[20%] h-[360px] w-[360px] bg-cyan" />
      <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
        {/* Left: form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">{t("title")}</h2>
          <p className="mt-3 max-w-md text-[15px] text-ink-muted">{t("subtitle")}</p>

          {status === "success" ? (
            <div className="mt-8 flex items-start gap-3 rounded-xl border border-green/30 bg-green/10 p-5">
              <Check className="mt-0.5 h-5 w-5 flex-shrink-0 text-green" strokeWidth={2.5} />
              <p className="text-[14px] text-ink">{t("success")}</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelCls} htmlFor="name">{t("name")} *</label>
                  <input id="name" name="name" className={inputCls} required />
                </div>
                <div>
                  <label className={labelCls} htmlFor="company">{t("company")} *</label>
                  <input id="company" name="company" className={inputCls} required />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={labelCls} htmlFor="email">{t("email")} *</label>
                  <input id="email" name="email" type="email" className={inputCls} required />
                </div>
                <div>
                  <label className={labelCls} htmlFor="phone">{t("phone")} <span className="text-ink-muted/60">({t("phoneOptional")})</span></label>
                  <input id="phone" name="phone" className={inputCls} />
                </div>
              </div>
              <div>
                <label className={labelCls} htmlFor="target">{t("target")} *</label>
                <input id="target" name="target" placeholder="uwbedrijf.nl" className={inputCls} required />
              </div>
              <div>
                <label className={labelCls} htmlFor="message">{t("message")} <span className="text-ink-muted/60">({t("messageOptional")})</span></label>
                <textarea id="message" name="message" rows={3} className={inputCls} />
              </div>

              <label className="flex items-start gap-2.5 text-[13px] text-ink-muted">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-0.5 h-4 w-4 flex-shrink-0 accent-cyan"
                />
                <span>{t("consent")} *</span>
              </label>

              {showErr && (
                <p className="flex items-center gap-1.5 text-[13px] text-red">
                  <AlertCircle className="h-4 w-4" strokeWidth={2} />
                  {t("consentRequired")}
                </p>
              )}
              {status === "error" && (
                <p className="flex items-center gap-1.5 text-[13px] text-red">
                  <AlertCircle className="h-4 w-4" strokeWidth={2} />
                  {t("error")}
                </p>
              )}

              <button
                type="submit"
                disabled={status === "sending"}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan px-6 py-3 text-[15px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98] disabled:opacity-60"
              >
                {status === "sending" ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} />
                    {t("sending")}
                  </>
                ) : (
                  t("submit")
                )}
              </button>
            </form>
          )}
        </motion.div>

        {/* Right: stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex flex-col justify-center gap-4"
        >
          {stats.map((s) => (
            <div key={s.text} className="flex items-center gap-4 rounded-xl border border-grid bg-card p-5">
              <span className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg bg-cyan/10">
                <s.icon className="h-5 w-5 text-cyan" strokeWidth={2} />
              </span>
              <p className="text-[14px] text-ink">{s.text}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
