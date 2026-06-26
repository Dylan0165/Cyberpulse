"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { Shield, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { TwoFactorPrompt } from "@/components/auth/TwoFactorPrompt";

// Client-only intro overlay (video needs the browser). Plays once per session.
const LogoIntro = dynamic(() => import("@/components/LogoIntro"), { ssr: false });

export default function LoginPage() {
  const router = useRouter();
  const { login, verify2fa } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [tempToken, setTempToken] = useState<string | null>(null);

  const routeAfterLogin = (user: any) =>
    router.push(user?.onboarding_completed ? "/dashboard" : "/onboarding");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      const res = await login(email, password);
      if (res?.requires_2fa) {
        setTempToken(res.temp_token); // show the 2FA prompt
        return;
      }
      routeAfterLogin(res?.user ?? res);
    } catch {
      toast.error("Ongeldig e-mailadres of wachtwoord");
    } finally {
      setSubmitting(false);
    }
  }

  async function handle2fa(code: string, useBackup: boolean) {
    if (submitting || !tempToken) return;
    setSubmitting(true);
    try {
      const user = await verify2fa(tempToken, code, useBackup);
      routeAfterLogin(user);
    } catch {
      toast.error(useBackup ? "Ongeldige herstelcode" : "Ongeldige code");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-app px-4 py-12">
      <LogoIntro />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl border border-grid bg-card2 shadow-glow-cyan">
            <Shield className="h-7 w-7 text-cyan" />
          </div>
          <h1 className="font-display text-2xl font-bold text-ink">Scanix</h1>
          <p className="mt-1 text-sm text-ink-muted">Inloggen</p>
        </div>

        {tempToken && (
          <div className="rounded-xl border border-grid bg-panel p-6 shadow-glow-cyan">
            <TwoFactorPrompt onVerify={handle2fa} busy={submitting} />
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className={`rounded-xl border border-grid bg-panel p-6 shadow-glow-cyan ${tempToken ? "hidden" : ""}`}
        >
          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-muted">
              E-mailadres
            </span>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="naam@bedrijf.nl"
              className="w-full rounded-lg border border-grid bg-card2 px-3 py-2.5 text-ink outline-none transition-colors focus:border-cyan"
            />
          </label>

          <label className="mb-6 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-muted">
              Wachtwoord
            </span>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-grid bg-card2 px-3 py-2.5 pr-11 text-ink outline-none transition-colors focus:border-cyan"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Wachtwoord verbergen" : "Wachtwoord tonen"}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-muted transition-colors hover:text-cyan"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </label>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-semibold text-app shadow-glow-cyan transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Inloggen
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-muted">
          Nog geen account?{" "}
          <Link href="/register" className="font-medium text-cyan hover:underline">
            Registreren &rarr;
          </Link>
        </p>
      </motion.div>
    </main>
  );
}
