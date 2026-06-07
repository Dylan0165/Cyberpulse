"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { dashboardApi, scansApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { toast } from "sonner";
import {
  Shield, ArrowLeft, ArrowRight, CheckCircle, Target, Globe, Server,
  Eye, EyeOff, Key, Lock, Unlock, Info,
} from "lucide-react";
import Link from "next/link";

// ── Constants ─────────────────────────────────────────────────────────────────

const SCAN_MODES = [
  {
    value: "blackbox",
    label: "Blackbox",
    description: "Extern perspectief — geen kennis of toegang. Simuleert een externe aanvaller.",
    icon: <Lock className="h-4 w-4" />,
    color: "border-red-500/40 bg-red-500/5",
    activeColor: "border-red-500 bg-red-500/10 ring-1 ring-red-500",
    badge: "text-red-500",
  },
  {
    value: "graybox",
    label: "Graybox",
    description: "Gedeeltelijke kennis — beperkte inloggegevens beschikbaar.",
    icon: <Eye className="h-4 w-4" />,
    color: "border-yellow-500/40 bg-yellow-500/5",
    activeColor: "border-yellow-500 bg-yellow-500/10 ring-1 ring-yellow-500",
    badge: "text-yellow-500",
  },
  {
    value: "whitebox",
    label: "Whitebox",
    description: "Volledige toegang — broncode, SSH, alle configuratie beschikbaar.",
    icon: <Unlock className="h-4 w-4" />,
    color: "border-green-500/40 bg-green-500/5",
    activeColor: "border-green-500 bg-green-500/10 ring-1 ring-green-500",
    badge: "text-green-500",
  },
];

const TARGET_TYPES = [
  { value: "web",       label: "Web Application",      description: "HTTP/HTTPS website of webapp" },
  { value: "api",       label: "API",                   description: "REST / GraphQL / SOAP API" },
  { value: "network",   label: "Netwerk / Infrastructuur", description: "IP-reeks of interne servers" },
  { value: "windows",   label: "Windows Server",        description: "Windows Active Directory / RDP" },
  { value: "linux",     label: "Linux Server",          description: "SSH / diensten op Linux" },
];

const PHASE_OPTIONS = [
  { value: "recon",        label: "Reconnaissance",          tools: "nmap, httpx-pd, whatweb",        alwaysEnabled: true },
  { value: "vulnerability",label: "Vulnerability Detection", tools: "nuclei, nikto",                  alwaysEnabled: false },
  { value: "webapp",       label: "Web Application Tests",   tools: "sqlmap, ffuf, nikto",            alwaysEnabled: false },
  { value: "network",      label: "Network Services",        tools: "nmap NSE",                       alwaysEnabled: false },
  { value: "auth",         label: "Authentication Tests",    tools: "hydra",                          alwaysEnabled: false },
  { value: "ssl",          label: "SSL/TLS Analysis",        tools: "testssl.sh",                     alwaysEnabled: false },
  { value: "osint",        label: "OSINT & Secrets",         tools: "theharvester, gitleaks",         alwaysEnabled: false },
];

const CUSTOM_MODULE_OPTIONS = [
  { value: "m09", label: "M09 — Business Logic Tester",    description: "IDOR, rate limiting, admin endpoints",         defaultChecked: false },
  { value: "m10", label: "M10 — CVE Correlator",           description: "Koppelt services aan CVEs via NVD API",        defaultChecked: true  },
  { value: "m11", label: "M11 — Visual Recon",             description: "Playwright screenshots van webdiensten",       defaultChecked: false },
  { value: "m12", label: "M12 — Smart Credential Attack",  description: "Doelspecifieke wordlist + Hydra",              defaultChecked: false },
  { value: "m13", label: "M13 — AI Adaptive Scanner",      description: "DeepSeek bepaalt follow-up scans",             defaultChecked: false },
  { value: "m14", label: "M14 — Scan Comparator",          description: "Diff met vorige scan op hetzelfde target",     defaultChecked: false },
];

const SCAN_TYPES = [
  { value: "quick",     label: "Quick Scan",         description: "Recon + vulnerability scan",             phases: ["recon","vulnerability","ssl"] },
  { value: "full",      label: "Volledige Pentest",   description: "Alle 7 fases — uitgebreide assessment",  phases: PHASE_OPTIONS.map(p => p.value) },
  { value: "web_only",  label: "Web Application",    description: "Recon, vuln scan, webapp testing",       phases: ["recon","vulnerability","webapp"] },
  { value: "network_only", label: "Netwerk Test",    description: "Recon, network services, auth",          phases: ["recon","network","auth"] },
  { value: "compliance",label: "Compliance Check",   description: "SSL/TLS + vulnerability scan",           phases: ["recon","vulnerability","ssl"] },
  { value: "custom",    label: "Aangepast",           description: "Kies zelf welke fases je wilt uitvoeren", phases: [] },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NewScanPage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-muted-foreground">Loading...</div>}>
      <NewScanContent />
    </Suspense>
  );
}

function NewScanContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Step state
  const [step, setStep] = useState(1);

  // Step 1 — Target
  const [selectedTarget, setSelectedTarget] = useState<string>(searchParams.get("target") ?? "");

  // Step 2 — Scan mode + type + target type
  const [scanMode, setScanMode] = useState<"blackbox" | "graybox" | "whitebox">("blackbox");
  const [scanType, setScanType] = useState("full");
  const [targetType, setTargetType] = useState("web");

  // Step 3 — Phases
  const [selectedPhases, setSelectedPhases] = useState<Set<string>>(
    new Set(SCAN_TYPES.find(t => t.value === "full")?.phases ?? [])
  );
  // Custom modules (m09–m14) — m10 on by default
  const [selectedModules, setSelectedModules] = useState<Set<string>>(
    new Set(CUSTOM_MODULE_OPTIONS.filter(m => m.defaultChecked).map(m => m.value))
  );

  // Step 4 — Credentials (only graybox / whitebox)
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [sshKey, setSshKey] = useState("");
  const [bearerToken, setBearerToken] = useState("");
  const [customHeaders, setCustomHeaders] = useState("");

  const STEPS = [
    { n: 1, label: "Target" },
    { n: 2, label: "Modus" },
    { n: 3, label: "Fases" },
    ...(scanMode !== "blackbox" ? [{ n: 4, label: "Credentials" }] : []),
    { n: scanMode !== "blackbox" ? 5 : 4, label: "Bevestigen" },
  ];
  const lastStep = STEPS[STEPS.length - 1].n;

  const { data: targets } = useQuery({
    queryKey: ["targets"],
    queryFn: dashboardApi.listTargets,
  });
  const allTargets = targets ?? [];

  const createScanMutation = useMutation({
    mutationFn: (data: any) => scansApi.create(data),
    onSuccess: (res) => {
      toast.success("Scan aangemaakt!");
      router.push(`/scans/${res.data.id}`);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Scan aanmaken mislukt");
    },
  });

  const handleCreate = () => {
    const creds: Record<string, string> = {};
    if (username)       creds.username       = username;
    if (password)       creds.password       = password;
    if (sshKey)         creds.ssh_key        = sshKey;
    if (bearerToken)    creds.bearer_token   = bearerToken;
    if (customHeaders)  creds.custom_headers = customHeaders;

    createScanMutation.mutate({
      target_id:   selectedTarget,
      scan_type:   scanType,
      // Kali phases + selected custom modules combined into one list
      phases:      [...Array.from(selectedPhases), ...Array.from(selectedModules)],
      scan_mode:   scanMode,
      target_type: targetType,
      credentials: creds,
    });
  };

  // When scan type changes, update default phases
  const handleScanTypeChange = (value: string) => {
    setScanType(value);
    if (value !== "custom") {
      const preset = SCAN_TYPES.find(t => t.value === value);
      setSelectedPhases(new Set(preset?.phases ?? []));
    }
  };

  const togglePhase = (phase: string) => {
    setSelectedPhases(prev => {
      const next = new Set(prev);
      if (next.has(phase)) next.delete(phase);
      else next.add(phase);
      return next;
    });
  };

  const toggleModule = (mod: string) => {
    setSelectedModules(prev => {
      const next = new Set(prev);
      if (next.has(mod)) next.delete(mod);
      else next.add(mod);
      return next;
    });
  };

  const selectedTarget_obj = allTargets.find((t: any) => t.id === selectedTarget);
  const currentScanType = SCAN_TYPES.find(t => t.value === scanType);

  const nextStep = () => setStep(s => s + 1);
  const prevStep = () => setStep(s => s - 1);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/scans">
          <Button variant="ghost" size="sm" className="text-[12px] uppercase tracking-[0.05em]">
            <ArrowLeft className="mr-2 h-4 w-4" />Terug
          </Button>
        </Link>
        <div>
          <h1 className="text-[18px] font-bold tracking-[0.05em]">Nieuwe Scan</h1>
          <p className="text-muted-foreground text-[12px]">Configureer en start een security assessment</p>
        </div>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-3 flex-wrap">
        {STEPS.map((s, i) => (
          <div key={s.n} className="flex items-center gap-2">
            <div className={`flex h-7 w-7 items-center justify-center text-[11px] font-medium border transition-colors ${
              step >= s.n ? "bg-foreground text-background border-foreground" : "text-muted-foreground border-border"
            }`}>
              {step > s.n ? <CheckCircle className="h-3 w-3" /> : s.n}
            </div>
            <span className="text-[11px] uppercase tracking-[0.05em]">{s.label}</span>
            {i < STEPS.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
          </div>
        ))}
      </div>

      {/* ── Step 1: Target ─────────────────────────────────────────────────── */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Target selecteren</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {allTargets.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-[12px]">
                <Target className="h-12 w-12 mx-auto mb-4 opacity-30" />
                Geen targets gevonden.
                <Link href="/targets"><Button className="ml-2 text-[12px]">Targets beheren</Button></Link>
              </div>
            ) : (
              <>
                {allTargets.map((target: any) => (
                  <div key={target.id} onClick={() => setSelectedTarget(target.id)}
                    className={`flex items-center gap-4 border p-3 cursor-pointer transition-colors ${
                      selectedTarget === target.id ? "border-foreground bg-secondary" : "hover:bg-secondary"
                    }`}>
                    <div className="flex h-8 w-8 items-center justify-center bg-secondary">
                      {target.target_type === "web_application" ? <Globe className="h-4 w-4" /> : <Server className="h-4 w-4" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-[13px] font-medium">{target.hostname ?? target.value}</p>
                      <p className="text-[10px] text-muted-foreground uppercase">{target.target_type?.replace("_", " ")}</p>
                    </div>
                    {selectedTarget === target.id && <CheckCircle className="h-4 w-4" />}
                  </div>
                ))}
                <Button className="w-full mt-4 text-[12px] uppercase" disabled={!selectedTarget} onClick={nextStep}>
                  Volgende <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Step 2: Scan mode + type + target type ──────────────────────────── */}
      {step === 2 && (
        <div className="space-y-4">
          {/* Scan Mode */}
          <Card>
            <CardHeader>
              <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Scan modus</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-3 gap-3">
              {SCAN_MODES.map((mode) => (
                <button key={mode.value} onClick={() => setScanMode(mode.value as any)}
                  className={`flex flex-col items-start gap-2 rounded-lg border p-4 text-left transition-all ${
                    scanMode === mode.value ? mode.activeColor : mode.color + " hover:opacity-90"
                  }`}>
                  <div className={`flex items-center gap-2 font-semibold text-[13px] ${scanMode === mode.value ? "" : mode.badge}`}>
                    {mode.icon} {mode.label}
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-snug">{mode.description}</p>
                </button>
              ))}
            </CardContent>
          </Card>

          {/* Target Type */}
          <Card>
            <CardHeader>
              <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Doelwit type</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {TARGET_TYPES.map((tt) => (
                <button key={tt.value} onClick={() => setTargetType(tt.value)}
                  className={`border rounded-lg p-3 text-left transition-colors ${
                    targetType === tt.value ? "border-foreground bg-secondary" : "hover:bg-secondary"
                  }`}>
                  <p className="text-[13px] font-medium">{tt.label}</p>
                  <p className="text-[11px] text-muted-foreground">{tt.description}</p>
                </button>
              ))}
            </CardContent>
          </Card>

          {/* Scan Type */}
          <Card>
            <CardHeader>
              <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Scan type</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {SCAN_TYPES.map((type) => (
                <div key={type.value} onClick={() => handleScanTypeChange(type.value)}
                  className={`border p-3 cursor-pointer transition-colors ${
                    scanType === type.value ? "border-foreground bg-secondary" : "hover:bg-secondary"
                  }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[13px] font-medium">{type.label}</p>
                      <p className="text-[11px] text-muted-foreground">{type.description}</p>
                    </div>
                    {type.value !== "custom" && (
                      <span className="text-[10px] text-muted-foreground">{type.phases.length} fases</span>
                    )}
                  </div>
                </div>
              ))}
              <div className="flex gap-2 mt-4">
                <Button variant="outline" onClick={prevStep} className="text-[12px] uppercase">
                  <ArrowLeft className="mr-2 h-4 w-4" />Terug
                </Button>
                <Button className="flex-1 text-[12px] uppercase" onClick={nextStep}>
                  Volgende <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Step 3: Phases ──────────────────────────────────────────────────── */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Scan fases selecteren</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {PHASE_OPTIONS.map((phase) => {
              const checked = selectedPhases.has(phase.value);
              return (
                <label key={phase.value}
                  className={`flex items-start gap-3 border rounded-lg p-3 cursor-pointer transition-colors ${
                    checked ? "border-foreground bg-secondary" : "hover:bg-secondary"
                  }`}>
                  <input type="checkbox" checked={checked}
                    onChange={() => togglePhase(phase.value)}
                    className="mt-0.5 accent-foreground" />
                  <div className="flex-1">
                    <span className="text-[13px] font-medium">{phase.label}</span>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{phase.tools}</p>
                  </div>
                </label>
              );
            })}

            {/* Custom Modules */}
            <div className="pt-3 mt-1 border-t border-border">
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2 font-medium">
                Custom Modules
              </p>
              {CUSTOM_MODULE_OPTIONS.map((mod) => {
                const checked = selectedModules.has(mod.value);
                return (
                  <label key={mod.value}
                    className={`flex items-start gap-3 border rounded-lg p-3 cursor-pointer transition-colors mb-2 ${
                      checked ? "border-purple-500/40 bg-purple-500/5" : "hover:bg-secondary"
                    }`}>
                    <input type="checkbox" checked={checked}
                      onChange={() => toggleModule(mod.value)}
                      className="mt-0.5 accent-purple-500" />
                    <div className="flex-1">
                      <span className="text-[13px] font-medium">{mod.label}</span>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{mod.description}</p>
                    </div>
                    {mod.defaultChecked && (
                      <span className="text-[9px] bg-purple-500/10 text-purple-600 px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5">
                        aanbevolen
                      </span>
                    )}
                  </label>
                );
              })}
            </div>

            <div className="flex gap-2 mt-4">
              <Button variant="outline" onClick={prevStep} className="text-[12px] uppercase">
                <ArrowLeft className="mr-2 h-4 w-4" />Terug
              </Button>
              <Button className="flex-1 text-[12px] uppercase"
                disabled={selectedPhases.size === 0} onClick={nextStep}>
                Volgende <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Step 4: Credentials (graybox/whitebox only) ─────────────────────── */}
      {step === 4 && scanMode !== "blackbox" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">
              Credentials ({scanMode === "whitebox" ? "Whitebox" : "Graybox"})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-[12px] text-muted-foreground">
              Alle credentials worden versleuteld opgeslagen en alleen gebruikt tijdens de scan.
            </p>

            <div className="grid gap-3">
              <div>
                <label className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1 block">Gebruikersnaam</label>
                <Input value={username} onChange={e => setUsername(e.target.value)}
                  placeholder="admin" className="text-[13px]" />
              </div>

              <div>
                <label className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1 block">Wachtwoord</label>
                <div className="relative">
                  <Input type={showPassword ? "text" : "password"}
                    value={password} onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••" className="text-[13px] pr-10" />
                  <button type="button" onClick={() => setShowPassword(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1 block">
                  Bearer Token / API Key
                </label>
                <Input value={bearerToken} onChange={e => setBearerToken(e.target.value)}
                  placeholder="eyJhbGci..." className="text-[13px] font-mono" />
              </div>

              {scanMode === "whitebox" && (
                <div>
                  <label className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1 block">
                    SSH Private Key
                  </label>
                  <textarea value={sshKey} onChange={e => setSshKey(e.target.value)}
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                    rows={4}
                    className="w-full rounded-md border bg-background px-3 py-2 text-[12px] font-mono focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
                </div>
              )}

              <div>
                <label className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1 block">
                  Custom Headers (optioneel, één per regel: Header: Value)
                </label>
                <textarea value={customHeaders} onChange={e => setCustomHeaders(e.target.value)}
                  placeholder={"X-Auth-Token: abc123\nX-Custom: value"}
                  rows={3}
                  className="w-full rounded-md border bg-background px-3 py-2 text-[12px] font-mono focus:outline-none focus:ring-2 focus:ring-ring resize-none" />
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <Button variant="outline" onClick={prevStep} className="text-[12px] uppercase">
                <ArrowLeft className="mr-2 h-4 w-4" />Terug
              </Button>
              <Button className="flex-1 text-[12px] uppercase" onClick={nextStep}>
                Volgende <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Last step: Confirm ───────────────────────────────────────────────── */}
      {step === lastStep && (
        <Card>
          <CardHeader>
            <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">
              Bevestigen &amp; starten
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="border p-4 space-y-3 text-[12px]">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Target</span>
                <span className="font-medium">{selectedTarget_obj?.hostname ?? selectedTarget_obj?.value ?? selectedTarget}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Doelwit type</span>
                <span className="font-medium">{TARGET_TYPES.find(t => t.value === targetType)?.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Scan modus</span>
                <span className={`font-medium ${
                  scanMode === "blackbox" ? "text-red-500" :
                  scanMode === "graybox" ? "text-yellow-500" : "text-green-500"
                }`}>{SCAN_MODES.find(m => m.value === scanMode)?.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Scan type</span>
                <span className="font-medium">{currentScanType?.label}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Fases</span>
                <span className="font-medium">{selectedPhases.size} geselecteerd</span>
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {Array.from(selectedPhases).map(p => (
                  <span key={p} className="text-[10px] bg-secondary border px-2 py-0.5 rounded">
                    {PHASE_OPTIONS.find(o => o.value === p)?.label ?? p}
                  </span>
                ))}
              </div>
              {scanMode !== "blackbox" && (username || password || bearerToken || sshKey) && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Credentials</span>
                  <span className="flex items-center gap-1 text-green-500 font-medium">
                    <Key className="h-3 w-3" />Ingesteld
                  </span>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={prevStep} className="text-[12px] uppercase">
                <ArrowLeft className="mr-2 h-4 w-4" />Terug
              </Button>
              <Button className="flex-1 text-[12px] uppercase" onClick={handleCreate}
                disabled={createScanMutation.isPending}>
                <Shield className="mr-2 h-4 w-4" />
                {createScanMutation.isPending ? "Bezig..." : "Scan Starten"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
