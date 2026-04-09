"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import { scansApi } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { toast } from "sonner";
import {
  Shield,
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Target,
  Globe,
  Server,
} from "lucide-react";
import Link from "next/link";

const SCAN_TYPES = [
  {
    value: "full",
    label: "Volledige Pentest",
    description: "Alle 8 fases � uitgebreide security assessment",
    phases: 8,
  },
  {
    value: "quick",
    label: "Quick Scan",
    description: "Recon + vulnerability scan",
    phases: 2,
  },
  {
    value: "web_only",
    label: "Web Application Test",
    description: "Web-gericht: recon, vuln scan, webapp testing",
    phases: 3,
  },
  {
    value: "network_only",
    label: "Netwerk Test",
    description: "Netwerk: recon, network services, auth testing",
    phases: 3,
  },
  {
    value: "compliance",
    label: "Compliance Check",
    description: "SSL/TLS + vulnerability scan voor compliance rapportage",
    phases: 2,
  },
];

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
  const preselectedTarget = searchParams.get("target");

  const [step, setStep] = useState(1);
  const [selectedTarget, setSelectedTarget] = useState<string>(
    preselectedTarget ?? ""
  );
  const [scanType, setScanType] = useState("full");

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
    createScanMutation.mutate({
      target_id: selectedTarget,
      scan_type: scanType,
    });
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/scans">
          <Button variant="ghost" size="sm" className="text-[12px] uppercase tracking-[0.05em]">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Terug
          </Button>
        </Link>
        <div>
          <h1 className="text-[18px] font-bold tracking-[0.05em]">Nieuwe Scan</h1>
          <p className="text-muted-foreground text-[12px]">
            Configureer en start een security assessment
          </p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-4">
        {[
          { n: 1, label: "Target" },
          { n: 2, label: "Type" },
          { n: 3, label: "Bevestigen" },
        ].map((s) => (
          <div key={s.n} className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center text-[11px] font-medium border ${
                step >= s.n
                  ? "bg-foreground text-background border-foreground"
                  : "text-muted-foreground border-border"
              }`}
            >
              {step > s.n ? <CheckCircle className="h-3 w-3" /> : s.n}
            </div>
            <span className="text-[11px] uppercase tracking-[0.05em]">{s.label}</span>
            {s.n < 3 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
          </div>
        ))}
      </div>

      {/* Step 1: Target */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Target selecteren</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {allTargets.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-[12px]">
                <Target className="h-12 w-12 mx-auto mb-4 opacity-30" />
                Geen targets gevonden. Voeg eerst een target toe.
                <br />
                <Link href="/targets">
                  <Button className="mt-4 text-[12px] uppercase">Naar Targets</Button>
                </Link>
              </div>
            ) : (
              <>
                {allTargets.map((target: any) => (
                  <div
                    key={target.id}
                    onClick={() => setSelectedTarget(target.id)}
                    className={`flex items-center gap-4 border p-3 cursor-pointer transition-colors ${
                      selectedTarget === target.id
                        ? "border-foreground bg-secondary"
                        : "hover:bg-secondary"
                    }`}
                  >
                    <div className="flex h-8 w-8 items-center justify-center bg-secondary">
                      {target.target_type === "web_application" ? (
                        <Globe className="h-4 w-4" />
                      ) : (
                        <Server className="h-4 w-4" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-[13px] font-medium">{target.hostname}</p>
                      <p className="text-[10px] text-muted-foreground uppercase">
                        {target.target_type?.replace("_", " ")}
                      </p>
                    </div>
                    {selectedTarget === target.id && (
                      <CheckCircle className="h-4 w-4" />
                    )}
                  </div>
                ))}
                <Button
                  className="w-full mt-4 text-[12px] uppercase"
                  disabled={!selectedTarget}
                  onClick={() => setStep(2)}
                >
                  Volgende <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 2: Scan Type */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Scan type</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {SCAN_TYPES.map((type) => (
              <div
                key={type.value}
                onClick={() => setScanType(type.value)}
                className={`border p-3 cursor-pointer transition-colors ${
                  scanType === type.value
                    ? "border-foreground bg-secondary"
                    : "hover:bg-secondary"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[13px] font-medium">{type.label}</p>
                    <p className="text-[11px] text-muted-foreground">{type.description}</p>
                  </div>
                  <span className="text-[10px] text-muted-foreground">{type.phases} fases</span>
                </div>
              </div>
            ))}
            <div className="flex gap-2 mt-4">
              <Button variant="outline" onClick={() => setStep(1)} className="text-[12px] uppercase">
                <ArrowLeft className="mr-2 h-4 w-4" /> Terug
              </Button>
              <Button className="flex-1 text-[12px] uppercase" onClick={() => setStep(3)}>
                Volgende <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Confirm */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">Bevestigen &amp; starten</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="border p-4 space-y-3">
              <div className="flex justify-between text-[12px]">
                <span className="text-muted-foreground">Target</span>
                <span className="font-medium">
                  {allTargets.find((t: any) => t.id === selectedTarget)?.hostname ?? selectedTarget}
                </span>
              </div>
              <div className="flex justify-between text-[12px]">
                <span className="text-muted-foreground">Type</span>
                <span className="font-medium">
                  {SCAN_TYPES.find((t) => t.value === scanType)?.label}
                </span>
              </div>
              <div className="flex justify-between text-[12px]">
                <span className="text-muted-foreground">Fases</span>
                <span className="font-medium">
                  {SCAN_TYPES.find((t) => t.value === scanType)?.phases}
                </span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(2)} className="text-[12px] uppercase">
                <ArrowLeft className="mr-2 h-4 w-4" /> Terug
              </Button>
              <Button
                className="flex-1 text-[12px] uppercase"
                onClick={handleCreate}
                disabled={createScanMutation.isPending}
              >
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
