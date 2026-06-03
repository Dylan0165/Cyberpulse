"use client";

import { useState, useTransition } from "react";
// Auth removed — netlab environment has no authentication
const useAuth = () => ({ getToken: async () => null as string | null });
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle,
  XCircle,
  Loader2,
  Globe,
  FileText,
  Server,
  Copy,
  RefreshCw,
} from "lucide-react";

type VerificationMethod = "dns" | "file" | "meta" | "ip";
type VerificationStatus = "idle" | "pending" | "verified" | "failed";

interface VerificationResult {
  method: VerificationMethod;
  status: VerificationStatus;
  detail?: string;
}

interface TargetVerificationProps {
  targetId: string;
  domain: string;
  /** Called when any method is successfully verified */
  onVerified?: () => void;
}

const METHOD_LABELS: Record<VerificationMethod, string> = {
  dns:  "DNS TXT Record",
  file: "HTML Meta Tag",
  meta: "Verification File",
  ip:   "IP Ownership",
};

const METHOD_ICONS: Record<VerificationMethod, React.ElementType> = {
  dns:  Globe,
  file: FileText,
  meta: FileText,
  ip:   Server,
};

export function TargetVerification({ targetId, domain, onVerified }: TargetVerificationProps) {
  const { getToken } = useAuth();
  const [results, setResults] = useState<Partial<Record<VerificationMethod, VerificationResult>>>({});
  const [token, setToken] = useState<string | null>(null);
  const [loadingToken, setLoadingToken] = useState(false);
  const [activeMethod, setActiveMethod] = useState<VerificationMethod | null>(null);
  const [checkingMethod, setCheckingMethod] = useState<VerificationMethod | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";

  /** Fetch a fresh verification token from the backend */
  async function fetchToken() {
    setLoadingToken(true);
    try {
      const jwt = await getToken();
      const res = await fetch(`${apiUrl}/api/v1/targets/${targetId}/verification-token`, {
        method: "POST",
        headers: jwt ? { Authorization: `Bearer ${jwt}` } : {},
      });
      if (!res.ok) throw new Error("Token ophalen mislukt");
      const data = await res.json();
      setToken(data.token as string);
    } catch (err) {
      console.error("fetchToken error:", err);
    } finally {
      setLoadingToken(false);
    }
  }

  /** Trigger server-side verification check */
  async function checkVerification(method: VerificationMethod) {
    setCheckingMethod(method);
    try {
      const jwt = await getToken();
      const res = await fetch(`${apiUrl}/api/v1/targets/${targetId}/verify`, {
        method: "POST",
        headers: {
          ...(jwt ? { Authorization: `Bearer ${jwt}` } : {}),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ method }),
      });
      const data = await res.json() as { verified: boolean; detail?: string };
      const status: VerificationStatus = data.verified ? "verified" : "failed";
      setResults(prev => ({
        ...prev,
        [method]: { method, status, detail: data.detail },
      }));
      if (data.verified) onVerified?.();
    } catch (err) {
      setResults(prev => ({
        ...prev,
        [method]: { method, status: "failed", detail: (err as Error).message },
      }));
    } finally {
      setCheckingMethod(null);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).catch(() => {});
  }

  const methods: VerificationMethod[] = ["dns", "file", "meta", "ip"];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm">Doelwit verifiëren</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Bewijs eigenaarschap van <span className="font-medium text-foreground">{domain}</span>
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={fetchToken}
          disabled={loadingToken}
          className="gap-1.5 text-xs h-8"
        >
          {loadingToken ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" />
          )}
          {token ? "Vernieuwen" : "Token ophalen"}
        </Button>
      </div>

      {/* Verification token display */}
      {token && (
        <div className="rounded-lg border bg-muted/40 px-3 py-2.5">
          <p className="text-[11px] text-muted-foreground mb-1.5 font-medium uppercase tracking-wide">
            Verificatietoken
          </p>
          <div className="flex items-center gap-2">
            <code className="text-xs font-mono text-foreground flex-1 break-all select-all">
              {token}
            </code>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 flex-shrink-0"
              onClick={() => copyToClipboard(token)}
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* Method cards */}
      <div className="space-y-2">
        {methods.map((method) => {
          const result = results[method];
          const Icon = METHOD_ICONS[method];
          const isChecking = checkingMethod === method;
          const isActive = activeMethod === method;
          const instructions = getInstructions(method, domain, token ?? "<token>");

          return (
            <div
              key={method}
              className={`border rounded-lg transition-all ${
                result?.status === "verified"
                  ? "border-emerald-500/50 bg-emerald-500/5"
                  : result?.status === "failed"
                  ? "border-destructive/50 bg-destructive/5"
                  : isActive
                  ? "border-primary/50 bg-primary/5"
                  : "border-border bg-card"
              }`}
            >
              {/* Method header */}
              <button
                className="w-full flex items-center gap-3 px-4 py-3 text-left"
                onClick={() => setActiveMethod(isActive ? null : method)}
              >
                <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                <span className="text-sm font-medium flex-1">{METHOD_LABELS[method]}</span>
                {result?.status === "verified" && (
                  <CheckCircle className="h-4 w-4 text-emerald-500" />
                )}
                {result?.status === "failed" && (
                  <XCircle className="h-4 w-4 text-destructive" />
                )}
                {result?.status === "pending" && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </button>

              {/* Instructions (expanded) */}
              {isActive && result?.status !== "verified" && (
                <div className="px-4 pb-4 border-t border-border/60 pt-3">
                  <div className="space-y-2.5">
                    {instructions.map((step, i) => (
                      <div key={i} className="text-xs text-muted-foreground">
                        <span className="text-foreground font-medium mr-1">{i + 1}.</span>
                        {step.label}
                        {step.value && (
                          <div className="mt-1 flex items-center gap-2">
                            <code className="flex-1 bg-muted border border-border rounded px-2 py-1 font-mono text-[11px] break-all">
                              {step.value}
                            </code>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 flex-shrink-0"
                              onClick={() => copyToClipboard(step.value!)}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Failure message */}
                  {result?.status === "failed" && result.detail && (
                    <div className="mt-3 text-xs text-destructive bg-destructive/10 rounded px-2.5 py-2">
                      {result.detail}
                    </div>
                  )}

                  {/* Verify button */}
                  <Button
                    className="mt-3 w-full h-8 text-xs gap-1.5"
                    size="sm"
                    onClick={() => checkVerification(method)}
                    disabled={isChecking || !token}
                  >
                    {isChecking && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    {isChecking ? "Controleren…" : "Verificatie controleren"}
                  </Button>
                  {!token && (
                    <p className="mt-1.5 text-[11px] text-muted-foreground text-center">
                      Haal eerst een verificatietoken op.
                    </p>
                  )}
                </div>
              )}

              {/* Success detail */}
              {result?.status === "verified" && result.detail && (
                <div className="px-4 pb-3 text-xs text-emerald-600 dark:text-emerald-400">
                  {result.detail}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Instruction builder ──────────────────────────────────────

interface InstructionStep {
  label: string;
  value?: string;
}

function getInstructions(
  method: VerificationMethod,
  domain: string,
  token: string
): InstructionStep[] {
  switch (method) {
    case "dns":
      return [
        { label: "Ga naar het DNS-beheer van je domeinnaam." },
        { label: "Voeg een TXT-record toe met de volgende waarde:", value: `cyberpulse-verify=${token}` },
        { label: "Sla op en wacht tot de DNS-wijziging is doorgevoerd (kan enkele minuten duren)." },
        { label: "Klik op 'Verificatie controleren'." },
      ];
    case "file":
      return [
        { label: "Maak een bestand aan op je webserver:", value: `https://${domain}/.well-known/cyberpulse-verify.txt` },
        { label: "De bestandsinhoud moet exact zijn:", value: token },
        { label: "Zorg dat het bestand publiek bereikbaar is via HTTP(S)." },
        { label: "Klik op 'Verificatie controleren'." },
      ];
    case "meta":
      return [
        { label: "Voeg de volgende meta-tag toe in de <head> van je homepage:" },
        { label: "Meta tag:", value: `<meta name="cyberpulse-verification" content="${token}">` },
        { label: "Zorg dat de wijziging live staat op:", value: `https://${domain}/` },
        { label: "Klik op 'Verificatie controleren'." },
      ];
    case "ip":
      return [
        { label: "Verifieer dat jij de eigenaar bent van het IP-adres.", },
        { label: "Het IP-adres van het doelwit moet overeenkomen met een IP-adres in jouw beheer." },
        { label: "Neem contact op via support als je hulp nodig hebt." },
      ];
  }
}
