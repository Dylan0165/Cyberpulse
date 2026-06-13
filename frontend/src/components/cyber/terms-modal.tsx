"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck, ExternalLink, Check } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { authApi } from "@/lib/api";

export function TermsModal({
  open,
  onAccepted,
}: {
  open: boolean;
  onAccepted: () => void;
}) {
  const [agreed, setAgreed] = useState(false);
  const [owner, setOwner] = useState(false);
  const [saving, setSaving] = useState(false);

  const canAccept = agreed && owner && !saving;

  const handleAccept = async () => {
    if (!canAccept) return;
    setSaving(true);
    try {
      await authApi.acceptTerms("1.0");
      toast.success("Voorwaarden geaccepteerd ✓");
      onAccepted();
    } catch {
      toast.error("Kon voorwaarden niet opslaan");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ type: "spring", stiffness: 280, damping: 26 }}
            className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-grid bg-card2 shadow-glow-cyan"
            style={{ background: "var(--bg-card)" }}
          >
            {/* Header */}
            <div className="border-b border-grid p-6">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-cyan" />
                <h2 className="font-display text-xl font-bold uppercase tracking-[0.04em] text-ink">
                  Gebruiksvoorwaarden <span className="text-cyan">CyberPulse</span>
                </h2>
              </div>
              <p className="mt-1 font-mono text-[12px] text-ink-muted">
                Lees en accepteer de voorwaarden om door te gaan
              </p>
            </div>

            {/* Scrollable terms */}
            <div className="max-h-[40vh] overflow-y-auto px-6 py-4 font-mono text-[12px] leading-relaxed text-ink-muted">
              <p className="mb-3 text-ink">Samenvatting van de voorwaarden:</p>
              <ol className="space-y-3">
                <li>
                  <span className="text-cyan">1. Toegestaan gebruik.</span> U mag CyberPulse uitsluitend
                  gebruiken voor security-assessments van systemen die u bezit of waarvoor u
                  uitdrukkelijke schriftelijke toestemming heeft.
                </li>
                <li>
                  <span className="text-cyan">2. Verboden gebruik.</span> Het testen van systemen zonder
                  toestemming, het verstoren van diensten of het misbruiken van verkregen toegang is
                  strikt verboden en kan strafbaar zijn.
                </li>
                <li>
                  <span className="text-cyan">3. Aansprakelijkheid.</span> CyberPulse wordt geleverd "as
                  is". U bent zelf volledig verantwoordelijk voor het gebruik en de gevolgen van de
                  uitgevoerde scans.
                </li>
                <li>
                  <span className="text-cyan">4. Eigendomsverificatie.</span> Voordat een scan start moet u
                  aantonen dat u eigenaar bent van het doelsysteem of toestemming heeft, via DNS- of
                  bestandsverificatie.
                </li>
                <li>
                  <span className="text-cyan">5. Gegevensverwerking.</span> Scanresultaten en credentials
                  worden versleuteld opgeslagen en uitsluitend gebruikt voor het uitvoeren van uw
                  assessments, conform de AVG/GDPR.
                </li>
                <li>
                  <span className="text-cyan">6. Toepasselijk recht.</span> Op deze voorwaarden is het
                  Nederlands recht van toepassing. Geschillen worden voorgelegd aan de bevoegde
                  Nederlandse rechter.
                </li>
              </ol>
              <Link
                href="/terms"
                target="_blank"
                className="mt-4 inline-flex items-center gap-1.5 text-cyan transition-colors hover:text-cyan/80"
              >
                Volledige voorwaarden lezen
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>

            {/* Checkboxes + action */}
            <div className="space-y-4 border-t border-grid p-6">
              <TermsCheckbox
                checked={agreed}
                onChange={() => setAgreed((v) => !v)}
                label="Ik heb de gebruiksvoorwaarden gelezen en ga akkoord"
              />
              <TermsCheckbox
                checked={owner}
                onChange={() => setOwner((v) => !v)}
                label="Ik bevestig dat ik eigenaar ben of toestemming heb om de opgegeven systemen te testen. Ik begrijp dat ongeautoriseerd testen strafbaar is."
              />

              <button
                type="button"
                onClick={handleAccept}
                disabled={!canAccept}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[13px] font-bold uppercase tracking-[0.12em] text-app shadow-glow-cyan transition-all duration-150 hover:scale-[1.01] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
              >
                {saving ? "Bezig met opslaan..." : "Accepteren en doorgaan"}
              </button>

              <Link
                href="/terms"
                target="_blank"
                className="block text-center font-mono text-[11px] text-ink-muted transition-colors hover:text-cyan"
              >
                Volledige voorwaarden lezen
              </Link>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function TermsCheckbox({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onChange}
      className="flex w-full items-start gap-3 text-left"
    >
      <span
        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors duration-150"
        style={{
          borderColor: checked ? "#00D4FF" : "#0A2035",
          background: checked ? "#00D4FF" : "transparent",
        }}
      >
        {checked && <Check className="h-3.5 w-3.5 text-app" />}
      </span>
      <span className="font-mono text-[12px] leading-snug text-ink-muted">{label}</span>
    </button>
  );
}
