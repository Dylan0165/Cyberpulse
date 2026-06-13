"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck, Copy, Globe, FileText } from "lucide-react";
import { toast } from "sonner";
import { targetsApi } from "@/lib/api";

type VerifyTab = "dns" | "file";

export function VerificationModal({
  open,
  targetId,
  token,
  domain,
  onVerified,
  onClose,
}: {
  open: boolean;
  targetId: string;
  token: string;
  domain: string;
  onVerified: () => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<VerifyTab>("dns");
  const [checking, setChecking] = useState(false);

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Gekopieerd naar klembord");
    } catch {
      toast.error("Kopiëren mislukt");
    }
  };

  const handleCheck = async (method: VerifyTab) => {
    setChecking(true);
    try {
      const resp: any = await targetsApi.verify(targetId, method);
      if (resp?.status === 200 || resp?.data?.verified) {
        toast.success("Systeem geverifieerd ✓");
        onVerified();
      } else {
        toast.error("Verificatie mislukt");
      }
    } catch (err: any) {
      toast.error(
        err?.response?.data?.detail?.error ??
          err?.response?.data?.detail ??
          "Verificatie mislukt"
      );
    } finally {
      setChecking(false);
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
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ type: "spring", stiffness: 280, damping: 26 }}
            onClick={(e) => e.stopPropagation()}
            className="flex max-h-[85vh] w-full max-w-xl flex-col overflow-hidden rounded-xl border border-grid bg-card2 shadow-glow-cyan"
            style={{ background: "var(--bg-card)" }}
          >
            {/* Header */}
            <div className="border-b border-grid p-6">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-cyan" />
                <h2 className="font-display text-lg font-bold uppercase tracking-[0.04em] text-ink">
                  Verifieer eigendom van <span className="text-cyan">{domain}</span>
                </h2>
              </div>
              <p className="mt-1 font-mono text-[12px] text-ink-muted">
                Bevestig dat u toestemming heeft om dit systeem te testen
              </p>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-grid px-6 pt-4">
              <TabButton
                active={tab === "dns"}
                onClick={() => setTab("dns")}
                icon={<Globe className="h-4 w-4" />}
                label="DNS verificatie"
              />
              <TabButton
                active={tab === "file"}
                onClick={() => setTab("file")}
                icon={<FileText className="h-4 w-4" />}
                label="Bestandsverificatie"
              />
            </div>

            {/* Body */}
            <div className="max-h-[45vh] overflow-y-auto p-6">
              {tab === "dns" ? (
                <div className="space-y-4">
                  <p className="font-mono text-[12px] text-ink-muted">
                    Voeg het volgende TXT record toe aan uw DNS-instellingen:
                  </p>
                  <CodeBlock
                    onCopy={() => copy(`cyberpulse-verify=${token}`)}
                    lines={[
                      `Naam:    @ (of ${domain})`,
                      `Type:    TXT`,
                      `Waarde:  cyberpulse-verify=${token}`,
                    ]}
                  />
                  <p className="font-mono text-[11px] text-ink-muted">
                    Het kan 5-15 minuten duren voordat DNS-wijzigingen actief zijn.
                  </p>
                  <CheckButton
                    onClick={() => handleCheck("dns")}
                    disabled={checking}
                  />
                </div>
              ) : (
                <div className="space-y-4">
                  <p className="font-mono text-[12px] text-ink-muted">
                    Plaats een bestand op uw webserver:
                  </p>
                  <CodeBlock
                    onCopy={() => copy(token)}
                    lines={[
                      `Pad:      /.well-known/cyberpulse-verify.txt`,
                      `Inhoud:   ${token}`,
                    ]}
                  />
                  <CheckButton
                    onClick={() => handleCheck("file")}
                    disabled={checking}
                  />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-grid p-6">
              <button
                type="button"
                onClick={onClose}
                className="w-full rounded-lg border border-grid bg-card2 px-4 py-2.5 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-colors duration-150 hover:border-cyan/50 hover:text-cyan"
              >
                Annuleren
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-2 border-b-2 px-3 pb-3 font-mono text-[12px] uppercase tracking-[0.08em] transition-colors duration-150 ${
        active
          ? "border-cyan text-cyan"
          : "border-transparent text-ink-muted hover:text-ink"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function CodeBlock({
  lines,
  onCopy,
}: {
  lines: string[];
  onCopy: () => void;
}) {
  return (
    <div className="relative rounded-lg border border-grid bg-app p-4">
      <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-[12px] leading-relaxed text-ink">
        {lines.join("\n")}
      </pre>
      <button
        type="button"
        onClick={onCopy}
        className="absolute right-2 top-2 inline-flex items-center gap-1.5 rounded-md border border-grid bg-card2 px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.08em] text-ink-muted transition-colors duration-150 hover:border-cyan/50 hover:text-cyan"
      >
        <Copy className="h-3 w-3" />
        Kopieer
      </button>
    </div>
  );
}

function CheckButton({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[13px] font-bold uppercase tracking-[0.12em] text-app shadow-glow-cyan transition-all duration-150 hover:scale-[1.01] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
    >
      {disabled ? "Controleren..." : "Verificatie controleren"}
    </button>
  );
}
