"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { dashboardApi, scansApi } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield, ArrowLeft, ArrowRight, Check, Target, Server,
  Eye, EyeOff, Key, Lock, Unlock, Rocket, Crosshair, Layers,
  Bug, Code2, Network, KeyRound, ShieldCheck, Search, Sparkles,
} from "lucide-react";
import Link from "next/link";
import { GlowCard } from "@/components/cyber/glow-card";
import { VerificationModal } from "@/components/cyber/verification-modal";

// ── Constants ─────────────────────────────────────────────────────────────────

const SCAN_MODES = [
  {
    value: "blackbox",
    label: "Blackbox",
    description: "Extern perspectief — geen kennis of toegang. Simuleert een externe aanvaller.",
    icon: <Lock className="h-5 w-5" />,
    color: "border-red-500/40 bg-red-500/5",
    activeColor: "border-red-500 bg-red-500/10 ring-1 ring-red-500",
    badge: "text-red-500",
    accent: "#FF2D55",
  },
  {
    value: "graybox",
    label: "Graybox",
    description: "Gedeeltelijke kennis — beperkte inloggegevens beschikbaar.",
    icon: <Eye className="h-5 w-5" />,
    color: "border-yellow-500/40 bg-yellow-500/5",
    activeColor: "border-yellow-500 bg-yellow-500/10 ring-1 ring-yellow-500",
    badge: "text-yellow-500",
    accent: "#FF8C00",
  },
  {
    value: "whitebox",
    label: "Whitebox",
    description: "Volledige toegang — broncode, SSH, alle configuratie beschikbaar.",
    icon: <Unlock className="h-5 w-5" />,
    color: "border-green-500/40 bg-green-500/5",
    activeColor: "border-green-500 bg-green-500/10 ring-1 ring-green-500",
    badge: "text-green-500",
    accent: "#00FF88",
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
  { value: "recon",        label: "Reconnaissance",          tools: "nmap, httpx-pd, whatweb",        alwaysEnabled: true,  icon: <Crosshair className="h-4 w-4" /> },
  { value: "vulnerability",label: "Vulnerability Detection", tools: "nuclei, nikto",                  alwaysEnabled: false, icon: <Bug className="h-4 w-4" /> },
  { value: "webapp",       label: "Web Application Tests",   tools: "sqlmap, ffuf, nikto",            alwaysEnabled: false, icon: <Code2 className="h-4 w-4" /> },
  { value: "network",      label: "Network Services",        tools: "nmap NSE",                       alwaysEnabled: false, icon: <Network className="h-4 w-4" /> },
  { value: "auth",         label: "Authentication Tests",    tools: "hydra",                          alwaysEnabled: false, icon: <KeyRound className="h-4 w-4" /> },
  { value: "ssl",          label: "SSL/TLS Analysis",        tools: "testssl.sh",                     alwaysEnabled: false, icon: <ShieldCheck className="h-4 w-4" /> },
  { value: "osint",        label: "OSINT & Secrets",         tools: "theharvester, gitleaks",         alwaysEnabled: false, icon: <Search className="h-4 w-4" /> },
];

const CUSTOM_MODULE_OPTIONS = [
  { value: "m09", label: "M09 — Business Logic Tester",    description: "IDOR, rate limiting, admin endpoints",         defaultChecked: false },
  { value: "m10", label: "M10 — CVE Correlator",           description: "Koppelt services aan CVEs via NVD API",        defaultChecked: true  },
  { value: "m11", label: "M11 — Visual Recon",             description: "Playwright screenshots van webdiensten",       defaultChecked: false },
  { value: "m12", label: "M12 — Smart Credential Attack",  description: "Doelspecifieke wordlist + Hydra",              defaultChecked: false },
  { value: "m13", label: "M13 — AI Adaptive Scanner",      description: "DeepSeek bepaalt follow-up scans",             defaultChecked: false },
  { value: "m14", label: "M14 — Scan Comparator",          description: "Diff met vorige scan op hetzelfde target",     defaultChecked: false },
  { value: "m15", label: "M15 — Autonomous Attack Agent",  description: "AI koppelt kwetsbaarheden samen in een aanvalsketen", defaultChecked: false },
  { value: "m16", label: "M16 — Exploit Verificatie",      description: "Bewijst welke kwetsbaarheden echt exploiteerbaar zijn via Metasploit check-modus", defaultChecked: false },
  { value: "m17", label: "M17 — Cloud Scanner",            description: "Controleert AWS, Azure en GCP op misconfiguraties en exposed storage", defaultChecked: false },
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
    <Suspense fallback={<div className="py-12 text-center font-mono text-sm text-ink-muted">Loading...</div>}>
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

  // Cloud credentials (optioneel, alleen relevant bij M17 — Cloud Scanner)
  const [showCloudCreds, setShowCloudCreds] = useState(false);
  const [cloudCreds, setCloudCreds] = useState({
    aws_access_key: "",
    aws_secret_key: "",
    aws_region: "eu-west-1",
  });

  const STEPS = [
    { n: 1, label: "Target" },
    { n: 2, label: "Modus" },
    { n: 3, label: "Fases" },
    ...(scanMode !== "blackbox" ? [{ n: 4, label: "Credentials" }] : []),
    { n: scanMode !== "blackbox" ? 5 : 4, label: "Bevestigen" },
  ];
  const lastStep = STEPS[STEPS.length - 1].n;

  // Verification flow state (set when backend returns 403 verification_required)
  const [verification, setVerification] = useState<{
    targetId: string;
    token: string;
    domain: string;
  } | null>(null);
  // Last payload sent — kept so we can retry after successful verification
  const [lastPayload, setLastPayload] = useState<any>(null);

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
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 429) {
        toast.error(detail?.message ?? "Te veel actieve scans. Probeer het later opnieuw.");
        return;
      }
      if (err?.response?.status === 403 && detail && typeof detail === "object") {
        if (detail.error === "verification_required") {
          const target_obj = allTargets.find((t: any) => t.id === selectedTarget);
          const domain =
            target_obj?.hostname ??
            target_obj?.value ??
            detail.target_id ??
            selectedTarget;
          setVerification({
            targetId: detail.target_id ?? selectedTarget,
            token: detail.token ?? "",
            domain,
          });
          return;
        }
        if (detail.error === "terms_not_accepted") {
          toast.error(detail.message ?? "Accepteer eerst de gebruiksvoorwaarden");
          return;
        }
        toast.error(detail.message ?? "Scan aanmaken mislukt");
        return;
      }
      toast.error(
        (typeof detail === "string" ? detail : null) ?? "Scan aanmaken mislukt"
      );
    },
  });

  const handleCreate = () => {
    const creds: Record<string, string> = {};
    if (username)       creds.username       = username;
    if (password)       creds.password       = password;
    if (sshKey)         creds.ssh_key        = sshKey;
    if (bearerToken)    creds.bearer_token   = bearerToken;
    if (customHeaders)  creds.custom_headers = customHeaders;

    const payload: any = {
      target_id:   selectedTarget,
      scan_type:   scanType,
      // Kali phases + selected custom modules combined into one list
      phases:      [...Array.from(selectedPhases), ...Array.from(selectedModules)],
      scan_mode:   scanMode,
      target_type: targetType,
      credentials: creds,
    };

    // Optionele cloud credentials — alleen meesturen als er iets is ingevuld.
    // Worden niet opgeslagen na de scan (backend verwerkt config.cloud_credentials).
    if (cloudCreds.aws_access_key || cloudCreds.aws_secret_key) {
      payload.config = {
        ...(payload.config ?? {}),
        cloud_credentials: {
          aws_access_key: cloudCreds.aws_access_key,
          aws_secret_key: cloudCreds.aws_secret_key,
          aws_region:     cloudCreds.aws_region,
        },
      };
    }

    setLastPayload(payload);
    createScanMutation.mutate(payload);
  };

  const handleVerified = () => {
    setVerification(null);
    if (lastPayload) {
      createScanMutation.mutate(lastPayload);
    }
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

  // ── Shared motion variants ────────────────────────────────────────────────
  const panelVariants = {
    initial: { opacity: 0, x: 24 },
    animate: { opacity: 1, x: 0 },
    exit:    { opacity: 0, x: -24 },
  };

  const listContainer = {
    animate: { transition: { staggerChildren: 0.05 } },
  };
  const listItem = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8 px-4 py-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/scans"
          className="flex items-center gap-2 rounded-lg border border-grid bg-card2 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-muted transition-colors duration-150 hover:border-cyan/50 hover:text-cyan"
        >
          <ArrowLeft className="h-4 w-4" />Terug
        </Link>
        <div>
          <h1 className="font-display text-2xl font-bold uppercase tracking-[0.06em] text-ink">
            Nieuwe <span className="text-cyan">Scan</span>
          </h1>
          <p className="font-mono text-[12px] text-ink-muted">
            Configureer en start een security assessment
          </p>
        </div>
      </div>

      {/* Progress indicator */}
      <div className="flex items-center">
        {STEPS.map((s, i) => {
          const done = step > s.n;
          const active = step === s.n;
          return (
            <div key={`${s.n}-${s.label}`} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-2">
                <motion.div
                  animate={{ scale: active ? 1.1 : 1 }}
                  transition={{ type: "spring", stiffness: 320, damping: 20 }}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border font-mono text-[12px] font-bold transition-colors duration-200"
                  style={
                    done || active
                      ? {
                          borderColor: "#00D4FF",
                          color: "#020408",
                          background: "#00D4FF",
                          boxShadow: active ? "0 0 18px rgba(0,212,255,0.5)" : undefined,
                        }
                      : { borderColor: "#0A2035", color: "#4A6880", background: "#080F18" }
                  }
                >
                  {done ? <Check className="h-4 w-4" /> : s.n}
                </motion.div>
                <span
                  className={`font-mono text-[10px] uppercase tracking-[0.1em] ${
                    active ? "text-cyan" : done ? "text-ink" : "text-ink-muted"
                  }`}
                >
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className="mx-2 mb-6 h-[2px] flex-1 overflow-hidden rounded-full bg-grid">
                  <motion.div
                    className="h-full bg-cyan"
                    initial={false}
                    animate={{ width: step > s.n ? "100%" : "0%" }}
                    transition={{ duration: 0.3 }}
                    style={{ boxShadow: "0 0 8px rgba(0,212,255,0.6)" }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {/* ── Step 1: Target + Scan mode + Target type ───────────────────────── */}
        {step === 1 && (
          <motion.div
            key="step-1"
            variants={panelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.25 }}
            className="space-y-6"
          >
            {/* Target select */}
            <div className="space-y-3">
              <SectionLabel icon={<Target className="h-3.5 w-3.5" />} text="Target selecteren" />
              {allTargets.length === 0 ? (
                <GlowCard glowColor="#FF8C00" className="p-8 text-center">
                  <Target className="mx-auto mb-4 h-12 w-12 text-ink-muted opacity-40" />
                  <p className="font-mono text-[13px] text-ink-muted">Geen targets gevonden.</p>
                  <Link
                    href="/targets"
                    className="mt-4 inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2 font-display text-[12px] font-bold uppercase tracking-[0.08em] text-app transition-transform duration-150 hover:scale-[1.02] active:scale-[0.98]"
                  >
                    Targets beheren
                  </Link>
                </GlowCard>
              ) : (
                <div className="relative">
                  <select
                    value={selectedTarget}
                    onChange={(e) => setSelectedTarget(e.target.value)}
                    className="w-full appearance-none rounded-lg border border-grid bg-card2 px-4 py-3 pr-10 font-mono text-[13px] text-ink outline-none transition-colors duration-150 focus:border-cyan focus:ring-1 focus:ring-cyan"
                  >
                    <option value="" disabled>
                      — Kies een target —
                    </option>
                    {allTargets.map((target: any) => (
                      <option key={target.id} value={target.id} className="bg-card2 text-ink">
                        {(target.hostname ?? target.value) +
                          " · " +
                          (target.target_type?.replace("_", " ") ?? "")}
                      </option>
                    ))}
                  </select>
                  <Server className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
                </div>
              )}
            </div>

            {/* Scan mode */}
            <div className="space-y-3">
              <SectionLabel icon={<Shield className="h-3.5 w-3.5" />} text="Scan modus" />
              <motion.div
                variants={listContainer}
                initial="initial"
                animate="animate"
                className="grid grid-cols-1 gap-3 sm:grid-cols-3"
              >
                {SCAN_MODES.map((mode) => {
                  const active = scanMode === mode.value;
                  return (
                    <motion.div key={mode.value} variants={listItem}>
                      <GlowCard
                        glowColor={mode.accent}
                        accentBorder={active ? mode.accent : undefined}
                        onClick={() => setScanMode(mode.value as any)}
                        className="h-full p-4"
                      >
                        <div
                          className="mb-2 flex items-center gap-2 font-display text-[14px] font-bold"
                          style={{ color: active ? mode.accent : undefined }}
                        >
                          <span style={{ color: mode.accent }}>{mode.icon}</span>
                          {mode.label}
                        </div>
                        <p className="font-mono text-[11px] leading-snug text-ink-muted">
                          {mode.description}
                        </p>
                      </GlowCard>
                    </motion.div>
                  );
                })}
              </motion.div>
            </div>

            {/* Target type */}
            <div className="space-y-3">
              <SectionLabel icon={<Layers className="h-3.5 w-3.5" />} text="Doelwit type" />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {TARGET_TYPES.map((tt) => {
                  const active = targetType === tt.value;
                  return (
                    <button
                      key={tt.value}
                      type="button"
                      onClick={() => setTargetType(tt.value)}
                      className={`rounded-lg border p-3 text-left transition-all duration-150 hover:scale-[1.02] active:scale-[0.98] ${
                        active
                          ? "border-cyan bg-cyan/5 shadow-glow-cyan"
                          : "border-grid bg-card2 hover:border-cyan/40"
                      }`}
                    >
                      <p className={`font-display text-[13px] font-semibold ${active ? "text-cyan" : "text-ink"}`}>
                        {tt.label}
                      </p>
                      <p className="font-mono text-[10px] leading-snug text-ink-muted">{tt.description}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            <NavButtons
              onNext={nextStep}
              nextDisabled={!selectedTarget}
            />
          </motion.div>
        )}

        {/* ── Step 2: Scan type ──────────────────────────────────────────────── */}
        {step === 2 && (
          <motion.div
            key="step-2"
            variants={panelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.25 }}
            className="space-y-6"
          >
            <SectionLabel icon={<Sparkles className="h-3.5 w-3.5" />} text="Scan type" />
            <motion.div
              variants={listContainer}
              initial="initial"
              animate="animate"
              className="grid grid-cols-1 gap-3 sm:grid-cols-2"
            >
              {SCAN_TYPES.map((type) => {
                const active = scanType === type.value;
                return (
                  <motion.div key={type.value} variants={listItem}>
                    <GlowCard
                      glowColor="#00D4FF"
                      accentBorder={active ? "#00D4FF" : undefined}
                      onClick={() => handleScanTypeChange(type.value)}
                      className="h-full p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className={`font-display text-[14px] font-semibold ${active ? "text-cyan" : "text-ink"}`}>
                            {type.label}
                          </p>
                          <p className="mt-0.5 font-mono text-[11px] text-ink-muted">{type.description}</p>
                        </div>
                        {type.value !== "custom" && (
                          <span className="shrink-0 rounded border border-grid bg-app px-2 py-0.5 font-mono text-[10px] text-ink-muted">
                            {type.phases.length} fases
                          </span>
                        )}
                      </div>
                    </GlowCard>
                  </motion.div>
                );
              })}
            </motion.div>

            <NavButtons onPrev={prevStep} onNext={nextStep} />
          </motion.div>
        )}

        {/* ── Step 3: Phases + custom modules ────────────────────────────────── */}
        {step === 3 && (
          <motion.div
            key="step-3"
            variants={panelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.25 }}
            className="space-y-6"
          >
            <SectionLabel icon={<Layers className="h-3.5 w-3.5" />} text="Selecteer scan fases" />
            <motion.div
              variants={listContainer}
              initial="initial"
              animate="animate"
              className="grid grid-cols-1 gap-3 sm:grid-cols-2"
            >
              {PHASE_OPTIONS.map((phase) => {
                const checked = selectedPhases.has(phase.value);
                return (
                  <motion.div key={phase.value} variants={listItem}>
                    <GlowCard
                      glowColor="#00D4FF"
                      accentBorder={checked ? "#00D4FF" : undefined}
                      onClick={() => togglePhase(phase.value)}
                      className="h-full p-4"
                    >
                      <div className="flex items-start gap-3">
                        <span className={checked ? "text-cyan" : "text-ink-muted"}>{phase.icon}</span>
                        <div className="flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <span className={`font-display text-[13px] font-semibold ${checked ? "text-cyan" : "text-ink"}`}>
                              {phase.label}
                            </span>
                            <CheckBox checked={checked} color="#00D4FF" />
                          </div>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {phase.tools.split(",").map((tool) => (
                              <span
                                key={tool}
                                className="rounded border border-grid bg-app px-1.5 py-0.5 font-mono text-[9px] text-ink-muted"
                              >
                                {tool.trim()}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </GlowCard>
                  </motion.div>
                );
              })}
            </motion.div>

            {/* Custom modules */}
            <div className="space-y-3 border-t border-grid pt-5">
              <SectionLabel icon={<Sparkles className="h-3.5 w-3.5" />} text="Custom Modules" accent="#A855F7" />
              <motion.div
                variants={listContainer}
                initial="initial"
                animate="animate"
                className="grid grid-cols-1 gap-3 sm:grid-cols-2"
              >
                {CUSTOM_MODULE_OPTIONS.map((mod) => {
                  const checked = selectedModules.has(mod.value);
                  return (
                    <motion.div key={mod.value} variants={listItem}>
                      <GlowCard
                        glowColor="#A855F7"
                        accentBorder={checked ? "#A855F7" : undefined}
                        onClick={() => toggleModule(mod.value)}
                        className="h-full p-4"
                      >
                        <div className="flex items-start gap-3">
                          <CheckBox checked={checked} color="#A855F7" />
                          <div className="flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <span
                                className="font-display text-[13px] font-semibold"
                                style={{ color: checked ? "#C084FC" : "#E8F4F8" }}
                              >
                                {mod.label}
                              </span>
                              {mod.defaultChecked && (
                                <span className="shrink-0 rounded bg-cyan/15 px-1.5 py-0.5 font-mono text-[8px] font-bold uppercase tracking-[0.1em] text-cyan">
                                  Recommended
                                </span>
                              )}
                            </div>
                            <p className="mt-0.5 font-mono text-[10px] leading-snug text-ink-muted">
                              {mod.description}
                            </p>
                          </div>
                        </div>
                      </GlowCard>
                    </motion.div>
                  );
                })}
              </motion.div>
            </div>

            {/* Cloud credentials (optioneel) — alleen tonen wanneer M17 geselecteerd is */}
            {selectedModules.has("m17") && (
              <div className="space-y-3 border-t border-grid pt-5">
                <button
                  type="button"
                  onClick={() => setShowCloudCreds((v) => !v)}
                  className="flex w-full items-center justify-between rounded-lg border border-grid bg-card2 px-4 py-3 text-left transition-colors duration-150 hover:border-cyan/50"
                >
                  <span className="flex items-center gap-2">
                    <Lock className="h-4 w-4 text-cyan" />
                    <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
                      Cloud credentials (optioneel)
                    </span>
                  </span>
                  <ArrowRight
                    className="h-4 w-4 text-ink-muted transition-transform duration-200"
                    style={{ transform: showCloudCreds ? "rotate(90deg)" : "none" }}
                  />
                </button>

                <AnimatePresence initial={false}>
                  {showCloudCreds && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="space-y-4 rounded-lg border border-grid bg-card2 p-5">
                        <Field label="AWS Access Key">
                          <input
                            value={cloudCreds.aws_access_key}
                            onChange={(e) =>
                              setCloudCreds((c) => ({ ...c, aws_access_key: e.target.value }))
                            }
                            placeholder="AKIA..."
                            className={inputCls}
                          />
                        </Field>

                        <Field label="AWS Secret Key">
                          <input
                            type="password"
                            value={cloudCreds.aws_secret_key}
                            onChange={(e) =>
                              setCloudCreds((c) => ({ ...c, aws_secret_key: e.target.value }))
                            }
                            placeholder="••••••••••••••••"
                            className={inputCls}
                          />
                        </Field>

                        <Field label="AWS Region">
                          <input
                            value={cloudCreds.aws_region}
                            onChange={(e) =>
                              setCloudCreds((c) => ({ ...c, aws_region: e.target.value }))
                            }
                            placeholder="eu-west-1"
                            className={inputCls}
                          />
                        </Field>

                        <p className="font-mono text-[10px] leading-snug text-ink-muted">
                          Credentials worden niet opgeslagen na de scan.
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            <NavButtons onPrev={prevStep} onNext={nextStep} nextDisabled={selectedPhases.size === 0} />
          </motion.div>
        )}

        {/* ── Step 4: Credentials (graybox/whitebox only) ────────────────────── */}
        {step === 4 && scanMode !== "blackbox" && (
          <motion.div
            key="step-4"
            variants={panelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.25 }}
            className="space-y-6"
          >
            <SectionLabel
              icon={<Key className="h-3.5 w-3.5" />}
              text={`Credentials (${scanMode === "whitebox" ? "Whitebox" : "Graybox"})`}
            />
            <GlowCard glowColor="#00D4FF" className="space-y-4 p-5">
              <p className="font-mono text-[11px] leading-snug text-ink-muted">
                Alle credentials worden versleuteld opgeslagen en alleen gebruikt tijdens de scan.
              </p>

              <Field label="Gebruikersnaam">
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  className={inputCls}
                />
              </Field>

              <Field label="Wachtwoord">
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className={`${inputCls} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted transition-colors hover:text-cyan"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </Field>

              <Field label="Bearer Token / API Key">
                <input
                  value={bearerToken}
                  onChange={(e) => setBearerToken(e.target.value)}
                  placeholder="eyJhbGci..."
                  className={inputCls}
                />
              </Field>

              {scanMode === "whitebox" && (
                <Field label="SSH Private Key">
                  <textarea
                    value={sshKey}
                    onChange={(e) => setSshKey(e.target.value)}
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                    rows={4}
                    className={`${inputCls} resize-none`}
                  />
                </Field>
              )}

              <Field label="Custom Headers (optioneel, één per regel: Header: Value)">
                <textarea
                  value={customHeaders}
                  onChange={(e) => setCustomHeaders(e.target.value)}
                  placeholder={"X-Auth-Token: abc123\nX-Custom: value"}
                  rows={3}
                  className={`${inputCls} resize-none`}
                />
              </Field>
            </GlowCard>

            <NavButtons onPrev={prevStep} onNext={nextStep} />
          </motion.div>
        )}

        {/* ── Last step: Confirm & Launch ────────────────────────────────────── */}
        {step === lastStep && (
          <motion.div
            key="step-confirm"
            variants={panelVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.25 }}
            className="space-y-6"
          >
            <SectionLabel icon={<Rocket className="h-3.5 w-3.5" />} text="Bevestigen & starten" />
            <GlowCard glowColor="#00FF88" accentBorder="#00D4FF" className="space-y-4 p-5">
              <SummaryRow
                label="Target"
                value={selectedTarget_obj?.hostname ?? selectedTarget_obj?.value ?? selectedTarget}
              />
              <SummaryRow
                label="Doelwit type"
                value={TARGET_TYPES.find((t) => t.value === targetType)?.label ?? targetType}
              />
              <SummaryRow
                label="Scan modus"
                value={SCAN_MODES.find((m) => m.value === scanMode)?.label ?? scanMode}
                valueClass={
                  scanMode === "blackbox"
                    ? "text-red-500"
                    : scanMode === "graybox"
                    ? "text-yellow-500"
                    : "text-green-500"
                }
              />
              <SummaryRow label="Scan type" value={currentScanType?.label ?? scanType} />
              <SummaryRow label="Fases" value={`${selectedPhases.size} geselecteerd`} />
              <SummaryRow label="Modules" value={`${selectedModules.size} geselecteerd`} />

              <div className="flex flex-wrap gap-1 border-t border-grid pt-3">
                {Array.from(selectedPhases).map((p) => (
                  <span
                    key={p}
                    className="rounded border border-grid bg-app px-2 py-0.5 font-mono text-[10px] text-ink"
                  >
                    {PHASE_OPTIONS.find((o) => o.value === p)?.label ?? p}
                  </span>
                ))}
              </div>

              {scanMode !== "blackbox" && (username || password || bearerToken || sshKey) && (
                <SummaryRow
                  label="Credentials"
                  value={
                    <span className="flex items-center justify-end gap-1 text-green-500">
                      <Key className="h-3 w-3" />Ingesteld
                    </span>
                  }
                />
              )}
            </GlowCard>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={prevStep}
                className="flex items-center gap-2 rounded-lg border border-grid bg-card2 px-4 py-3 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-all duration-150 hover:border-cyan/50 hover:text-cyan active:scale-[0.98]"
              >
                <ArrowLeft className="h-4 w-4" />Terug
              </button>
              <motion.button
                type="button"
                onClick={handleCreate}
                disabled={createScanMutation.isPending}
                whileHover={{ scale: createScanMutation.isPending ? 1 : 1.02 }}
                whileTap={{ scale: createScanMutation.isPending ? 1 : 0.98 }}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[13px] font-bold uppercase tracking-[0.12em] text-app shadow-glow-cyan transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {createScanMutation.isPending ? (
                  <>
                    <motion.span
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                      className="inline-flex"
                    >
                      <Rocket className="h-4 w-4" />
                    </motion.span>
                    Scan starten...
                  </>
                ) : (
                  <>
                    <Rocket className="h-4 w-4" />Launch Scan
                  </>
                )}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {verification && (
        <VerificationModal
          open
          targetId={verification.targetId}
          token={verification.token}
          domain={verification.domain}
          onVerified={handleVerified}
          onClose={() => setVerification(null)}
        />
      )}
    </div>
  );
}

// ── Small presentational helpers ───────────────────────────────────────────────

const inputCls =
  "w-full rounded-lg border border-grid bg-app px-3 py-2.5 font-mono text-[12px] text-ink outline-none transition-colors duration-150 placeholder:text-ink-muted/60 focus:border-cyan focus:ring-1 focus:ring-cyan";

function SectionLabel({
  icon,
  text,
  accent = "#00D4FF",
}: {
  icon: React.ReactNode;
  text: string;
  accent?: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span style={{ color: accent }}>{icon}</span>
      <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">{text}</span>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block font-mono text-[10px] uppercase tracking-[0.12em] text-ink-muted">
        {label}
      </label>
      {children}
    </div>
  );
}

function CheckBox({ checked, color }: { checked: boolean; color: string }) {
  return (
    <span
      className="flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors duration-150"
      style={{
        borderColor: checked ? color : "#0A2035",
        background: checked ? color : "transparent",
      }}
    >
      {checked && <Check className="h-3.5 w-3.5 text-app" />}
    </span>
  );
}

function SummaryRow({
  label,
  value,
  valueClass = "text-ink",
}: {
  label: string;
  value: React.ReactNode;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink-muted">{label}</span>
      <span className={`text-right font-display text-[13px] font-semibold ${valueClass}`}>{value}</span>
    </div>
  );
}

function NavButtons({
  onPrev,
  onNext,
  nextDisabled = false,
}: {
  onPrev?: () => void;
  onNext: () => void;
  nextDisabled?: boolean;
}) {
  return (
    <div className="flex gap-3 pt-2">
      {onPrev && (
        <button
          type="button"
          onClick={onPrev}
          className="flex items-center gap-2 rounded-lg border border-grid bg-card2 px-4 py-3 font-mono text-[12px] uppercase tracking-[0.1em] text-ink-muted transition-all duration-150 hover:border-cyan/50 hover:text-cyan active:scale-[0.98]"
        >
          <ArrowLeft className="h-4 w-4" />Terug
        </button>
      )}
      <motion.button
        type="button"
        onClick={onNext}
        disabled={nextDisabled}
        whileHover={{ scale: nextDisabled ? 1 : 1.02 }}
        whileTap={{ scale: nextDisabled ? 1 : 0.98 }}
        className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-cyan px-4 py-3 font-display text-[12px] font-bold uppercase tracking-[0.12em] text-app shadow-glow-cyan transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Volgende <ArrowRight className="h-4 w-4" />
      </motion.button>
    </div>
  );
}
