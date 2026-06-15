"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { scansApi, targetsApi } from "@/lib/api";
import { FindingsTable } from "@/components/scan/findings-table";
import { RiskGauge } from "@/components/reports/risk-gauge";
import type { ReportData, Target } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { statusLabel, severityLabel, scanTypeLabel } from "@/lib/labels";
import {
  ArrowLeft, Download, ExternalLink, Share2, Shield,
  AlertTriangle, CheckCircle2, Clock, XCircle,
} from "lucide-react";

const RISK_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-black",
  LOW: "bg-blue-500 text-white",
  INFO: "bg-gray-400 text-white",
};

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.id as string;

  const [report, setReport] = useState<ReportData | null>(null);
  const [target, setTarget] = useState<Target | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const { data: reportData } = await scansApi.getReport(scanId);
        setReport(reportData);
        // Load target info if available
        if (reportData.scan_id) {
          try {
            const { data: scanData } = await scansApi.get(scanId);
            const { data: targetData } = await targetsApi.get(scanData.target_id);
            setTarget(targetData);
          } catch { /* target info is optional */ }
        }
      } catch (e: any) {
        setError("Rapport niet gevonden");
      }
      setLoading(false);
    };
    load();
  }, [scanId]);

  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/reports/${scanId}`);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 3000);
    } catch { /* ignore */ }
  };

  const handleDownloadPdf = () => {
    const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    window.open(`${baseUrl}/api/scans/${scanId}/report/pdf`, "_blank");
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );

  if (error || !report) return (
    <div className="flex flex-col items-center justify-center h-64 space-y-4">
      <XCircle className="h-12 w-12 text-destructive" />
      <p className="text-sm text-muted-foreground">{error || "Rapport niet gevonden"}</p>
      <Button variant="outline" onClick={() => router.push("/scans")}>
        <ArrowLeft className="mr-2 h-4 w-4" /> Terug naar scans
      </Button>
    </div>
  );

  const filteredFindings = activeCategory
    ? report.findings.filter(f => f.owasp_category === activeCategory)
    : report.findings;

  const categories = Array.from(new Set(
    report.findings.map(f => f.owasp_category).filter(Boolean) as string[]
  ));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Button variant="ghost" size="sm" onClick={() => router.push(`/scans/${scanId}`)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-2xl font-bold">Beveiligingsrapport</h1>
          </div>
          <p className="text-sm text-muted-foreground pl-10">
            {report.target} · {scanTypeLabel(report.scan_type)} ·{" "}
            {target ? `Geverifieerd systeem` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleShare}>
            <Share2 className="mr-1 h-3 w-3" />
            {shareCopied ? "Link gekopieerd!" : "Rapport delen"}
          </Button>
          <Button size="sm" onClick={handleDownloadPdf}>
            <Download className="mr-1 h-3 w-3" /> PDF downloaden
          </Button>
        </div>
      </div>

      {/* Risk gauge + summary stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="flex flex-col items-center justify-center py-8">
          <CardContent className="flex flex-col items-center space-y-4 pt-0">
            <RiskGauge score={report.overall_score} size={160} />
            <p className="text-center text-sm text-muted-foreground">
              Algehele beveiligingsscore
            </p>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Overzicht bevindingen</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-5 gap-2">
              {[
                { label: severityLabel("critical"), count: report.critical_count, color: "bg-red-600" },
                { label: severityLabel("high"), count: report.high_count, color: "bg-orange-500" },
                { label: severityLabel("medium"), count: report.medium_count, color: "bg-yellow-500" },
                { label: severityLabel("low"), count: report.low_count, color: "bg-blue-500" },
                { label: severityLabel("info"), count: report.info_count, color: "bg-gray-400" },
              ].map(({ label, count, color }) => (
                <div key={label} className="text-center">
                  <div className={`${color} rounded py-2 px-1`}>
                    <p className="text-white font-bold text-xl">{count}</p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{label}</p>
                </div>
              ))}
            </div>

            {/* Severity bar chart */}
            <div className="space-y-1.5">
              {report.category_scores?.map(cat => (
                <div key={cat.category} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-32 truncate">{cat.category}</span>
                  <div className="flex-1 bg-muted rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-primary"
                      style={{ width: `${(cat.score / cat.max_score) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground w-10 text-right">
                    {Math.round((cat.score / cat.max_score) * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Executive Summary */}
      {report.executive_summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Samenvatting voor management
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {report.executive_summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Technical Summary */}
      {report.technical_summary && (
        <Card>
          <CardHeader><CardTitle className="text-base">Technische samenvatting</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed font-mono text-muted-foreground whitespace-pre-line">
              {report.technical_summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Remediation Roadmap */}
      {report.remediation_roadmap && Object.keys(report.remediation_roadmap).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Stappenplan voor herstel
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {Object.entries(report.remediation_roadmap).map(([timeframe, items]) => (
                <div key={timeframe}>
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <h4 className="font-semibold text-sm">{timeframe}</h4>
                  </div>
                  <ul className="space-y-2">
                    {(items as any[]).map((item, i) => (
                      <li key={i} className="text-sm flex items-start gap-2 text-muted-foreground">
                        <span className="text-primary mt-0.5 shrink-0">›</span>
                        <span>{item.action || item.title || String(item)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Findings */}
      {report.findings?.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <CardTitle>
                Bevindingen
                <span className="text-muted-foreground font-normal text-sm ml-2">
                  ({filteredFindings.length}{activeCategory ? ` van ${report.findings.length}` : ""})
                </span>
              </CardTitle>
              <div className="flex flex-wrap gap-1">
                <Button
                  size="sm"
                  variant={activeCategory === null ? "default" : "outline"}
                  className="h-6 text-xs px-2"
                  onClick={() => setActiveCategory(null)}
                >
                  Alle
                </Button>
                {categories.map(cat => (
                  <Button
                    key={cat}
                    size="sm"
                    variant={activeCategory === cat ? "default" : "outline"}
                    className="h-6 text-xs px-2"
                    onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
                  >
                    {cat}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <FindingsTable findings={filteredFindings} />
          </CardContent>
        </Card>
      )}

      {/* Scan Metadata */}
      <Card>
        <CardHeader><CardTitle className="text-base">Scangegevens</CardTitle></CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-muted-foreground">Scan-ID</dt>
              <dd className="font-mono text-xs mt-0.5 truncate">{report.scan_id}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Systeem</dt>
              <dd className="mt-0.5">{report.target}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Soort test</dt>
              <dd className="mt-0.5">{scanTypeLabel(report.scan_type)}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Onderdelen</dt>
              <dd className="mt-0.5">{report.phases_completed?.join(", ")}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
