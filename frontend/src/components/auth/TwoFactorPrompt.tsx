"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";

/**
 * Shown after a correct password when the account has 2FA. Auto-submits the
 * 6-digit TOTP code; offers a recovery-code fallback.
 */
export function TwoFactorPrompt({
  onVerify,
  busy,
}: {
  onVerify: (code: string, useBackup: boolean) => void;
  busy: boolean;
}) {
  const [code, setCode] = useState("");
  const [useBackup, setUseBackup] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, [useBackup]);

  // Auto-submit once a full TOTP code is entered.
  useEffect(() => {
    if (!useBackup && code.length === 6 && !busy) onVerify(code, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, useBackup]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col items-center text-center">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl border border-grid bg-card2 shadow-glow-cyan">
          <ShieldCheck className="h-6 w-6 text-cyan" />
        </div>
        <h2 className="font-display text-lg font-bold text-ink">Twee-factor verificatie</h2>
        <p className="mt-1 text-[13px] text-ink-muted">
          {useBackup ? "Voer een herstelcode in." : "Voer de 6-cijferige code uit uw authenticator-app in."}
        </p>
      </div>

      <input
        ref={inputRef}
        value={code}
        onChange={(e) =>
          setCode(useBackup ? e.target.value.trim() : e.target.value.replace(/\D/g, "").slice(0, 6))
        }
        onKeyDown={(e) => e.key === "Enter" && code && !busy && onVerify(code, useBackup)}
        inputMode={useBackup ? "text" : "numeric"}
        placeholder={useBackup ? "herstelcode" : "000000"}
        className="w-full rounded-lg border border-grid bg-card2 px-4 py-3 text-center font-mono text-[18px] tracking-[0.3em] text-ink outline-none focus:border-cyan/60"
      />

      <button
        type="button"
        disabled={busy || !code}
        onClick={() => onVerify(code, useBackup)}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[13px] font-bold uppercase tracking-[0.1em] text-app shadow-glow-cyan disabled:opacity-50"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Verifieer"}
      </button>

      <button
        type="button"
        onClick={() => {
          setUseBackup((v) => !v);
          setCode("");
        }}
        className="block w-full text-center font-mono text-[12px] text-ink-muted hover:text-cyan"
      >
        {useBackup ? "Gebruik authenticator-code" : "Gebruik herstelcode"}
      </button>
    </div>
  );
}

export default TwoFactorPrompt;
