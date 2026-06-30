"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2, AlertCircle, ArrowRight } from "lucide-react";
import { Link } from "@/lib/navigation";
import { APP_URL } from "@/lib/appUrl";

type Status = "idle" | "sending" | "error";

const inputCls =
  "w-full rounded-lg border border-grid bg-bg-secondary px-3.5 py-2.5 text-[14px] text-ink placeholder:text-ink-muted/50 outline-none transition-colors focus:border-cyan";

export function LoginForm() {
  const t = useTranslations("login");
  const [status, setStatus] = useState<Status>("idle");
  const [showPw, setShowPw] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget).entries());
    setStatus("sending");
    try {
      const res = await fetch(`${APP_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: data.email, password: data.password }),
      });
      if (!res.ok) {
        setStatus("error");
        return;
      }
      // Session cookie is now set on app.scanix.nl — hand off to the dashboard.
      window.location.href = `${APP_URL}/dashboard`;
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center px-5 py-16">
      <div className="glow-accent left-1/2 top-0 h-[360px] w-[360px] -translate-x-1/2 bg-cyan" />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-md"
      >
        <div className="mb-7 text-center">
          <Link href="/" className="font-display text-2xl font-bold tracking-tight">
            <span className="text-cyan">Scan</span>
            <span className="text-ink">ix</span>
          </Link>
        </div>

        <div className="rounded-2xl border border-grid bg-card p-8 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.7)]">
          <h1 className="font-display text-2xl font-bold tracking-tight text-ink">{t("title")}</h1>
          <p className="mt-1.5 text-[14px] text-ink-muted">{t("subtitle")}</p>

          <form onSubmit={handleSubmit} className="mt-7 space-y-4">
            <div>
              <label className="mb-1.5 block text-[12px] font-medium text-ink-muted" htmlFor="email">
                {t("email")}
              </label>
              <input id="email" name="email" type="email" autoComplete="email" required className={inputCls} />
            </div>

            <div>
              <label className="mb-1.5 block text-[12px] font-medium text-ink-muted" htmlFor="password">
                {t("password")}
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPw ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  className={`${inputCls} pr-11`}
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-muted transition-colors hover:text-ink"
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff className="h-4.5 w-4.5" strokeWidth={2} /> : <Eye className="h-4.5 w-4.5" strokeWidth={2} />}
                </button>
              </div>
            </div>

            {status === "error" && (
              <p className="flex items-center gap-1.5 text-[13px] text-red">
                <AlertCircle className="h-4 w-4" strokeWidth={2} />
                {t("error")}
              </p>
            )}

            <button
              type="submit"
              disabled={status === "sending"}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-6 py-2.5 text-[15px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98] disabled:opacity-60"
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
        </div>

        <p className="mt-6 text-center text-[14px] text-ink-muted">
          <Link href="/contact" className="inline-flex items-center gap-1 text-cyan transition-colors hover:text-cyan/80">
            {t("noAccount")}
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
