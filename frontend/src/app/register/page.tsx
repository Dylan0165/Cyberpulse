"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Shield, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";

type Strength = "weak" | "medium" | "strong";

function passwordStrength(pw: string): Strength {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score >= 4) return "strong";
  if (score >= 2) return "medium";
  return "weak";
}

const STRENGTH_META: Record<Strength, { label: string; color: string; width: string }> = {
  weak: { label: "Zwak", color: "#FF2D55", width: "33%" },
  medium: { label: "Gemiddeld", color: "#FFD60A", width: "66%" },
  strong: { label: "Sterk", color: "#00FF88", width: "100%" },
};

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const strength = useMemo(() => passwordStrength(password), [password]);

  const passwordTooShort = password.length > 0 && password.length < 8;
  const mismatch = confirm.length > 0 && confirm !== password;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;

    if (password.length < 8) {
      toast.error("Wachtwoord moet minimaal 8 tekens bevatten");
      return;
    }
    if (password !== confirm) {
      toast.error("Wachtwoorden komen niet overeen");
      return;
    }

    setSubmitting(true);
    try {
      await register({
        email,
        password,
        name,
        company_name: companyName,
      });
      router.push("/onboarding");
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 400 && detail) {
        toast.error(
          typeof detail === "string" ? detail : "E-mailadres is al in gebruik"
        );
      } else {
        toast.error("Account aanmaken mislukt. Probeer het opnieuw.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-app px-4 py-12">
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
          <h1 className="font-display text-2xl font-bold text-ink">Account aanmaken</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Start vandaag met CyberPulse
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-grid bg-panel p-6 shadow-glow-cyan"
        >
          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-muted">Naam</span>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Jan Jansen"
              className="w-full rounded-lg border border-grid bg-card2 px-3 py-2.5 text-ink outline-none transition-colors focus:border-cyan"
            />
          </label>

          <label className="mb-4 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-muted">
              Bedrijfsnaam
            </span>
            <input
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Uw bedrijf B.V."
              className="w-full rounded-lg border border-grid bg-card2 px-3 py-2.5 text-ink outline-none transition-colors focus:border-cyan"
            />
          </label>

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

          <label className="mb-2 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-muted">
              Wachtwoord
            </span>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                required
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimaal 8 tekens"
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

          {password.length > 0 && (
            <div className="mb-4">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-card2">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: STRENGTH_META[strength].width,
                    background: STRENGTH_META[strength].color,
                  }}
                />
              </div>
              <p
                className="mt-1 text-xs"
                style={{ color: STRENGTH_META[strength].color }}
              >
                {STRENGTH_META[strength].label}
              </p>
            </div>
          )}
          {passwordTooShort && (
            <p className="mb-4 -mt-2 text-xs text-neon-red">
              Wachtwoord moet minimaal 8 tekens bevatten
            </p>
          )}

          <label className="mb-2 block">
            <span className="mb-1.5 block text-sm font-medium text-ink-muted">
              Wachtwoord herhalen
            </span>
            <input
              type={showPassword ? "text" : "password"}
              required
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Herhaal uw wachtwoord"
              className="w-full rounded-lg border border-grid bg-card2 px-3 py-2.5 text-ink outline-none transition-colors focus:border-cyan"
              style={mismatch ? { borderColor: "#FF2D55" } : undefined}
            />
          </label>
          {mismatch && (
            <p className="mb-4 text-xs text-neon-red">
              Wachtwoorden komen niet overeen
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-2.5 font-semibold text-app shadow-glow-cyan transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Account aanmaken
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-muted">
          Al een account?{" "}
          <Link href="/login" className="font-medium text-cyan hover:underline">
            Inloggen
          </Link>
        </p>
      </motion.div>
    </main>
  );
}
