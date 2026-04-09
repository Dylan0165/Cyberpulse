"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { scansApi, reportsApi } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import {
  Shield,
  ArrowLeft,
  Play,
  StopCircle,
  Download,
  Share2,
  Copy,
  FileText,
  AlertTriangle,
  CheckCircle,
  Activity,
  Clock,
} from "lucide-react";
import Link from "next/link";
import { ScanProgress } from "@/components/scan/scan-progress";
import { FindingsTable } from "@/components/scan/findings-table";
import type { Finding } from "@/types";

export default function ScanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const scanId = params.id as string;
  const [activeTab, setActiveTab] = useState<"progress" | "findings" | "report">("progress");

  const { data: scan, isLoading } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => scansApi.get(scanId).then((r) => r.data),
    refetchInterval: (query) => {
      const s = query.state.data;
      if (s && ["running", "analyzing"].includes(s.status)) return 3000;
      return false;
    },
  });

  const startMutation = useMutation({
    mutationFn: () => scansApi.start(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scan", scanId] });
      toast.success("Scan started!");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Failed to start scan");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => scansApi.cancel(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scan", scanId] });
      toast.success("Scan cancelled");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Failed to cancel scan");
    },
  });

  const { data: report } = useQuery({
    queryKey: ["scan-report", scanId],
    queryFn: () => scansApi.getReport(scanId).then((r) => r.data),
    enabled: scan?.status === "completed",
  });

  if (isLoading) {
    return <div className="text-center py-12 text-muted-foreground">Loading...</div>;
  }

  if (!scan) {
    return <div className="text-center py-12 text-muted-foreground">Scan not found</div>;
  }

  const findings: Finding[] = report?.findings ?? [];

  const showStartButton = scan.status === "pending";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/scans">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            Scan Details
          </h1>
          <p className="text-muted-foreground">
            {scan.scan_type.replace("_", " ")} scan &bull; Created{" "}
            {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          {showStartButton && (
            <Button onClick={() => startMutation.mutate()}>
              <Play className="mr-2 h-4 w-4" />
              Start Scan
            </Button>
          )}
          {scan.status === "running" && (
            <Button
              variant="destructive"
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
            >
              <StopCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
          {scan.status === "completed" && (
            <>
              <Button
                variant="outline"
                onClick={async () => {
                  const res = await reportsApi.downloadPdf(scanId);
                  const blob = new Blob([res.data]);
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `scan-${scanId}.pdf`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                <Download className="mr-2 h-4 w-4" />
                PDF
              </Button>
              <Button
                variant="outline"
                onClick={async () => {
                  const res = await reportsApi.downloadJson(scanId);
                  const blob = new Blob([res.data]);
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `scan-${scanId}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                <FileText className="mr-2 h-4 w-4" />
                JSON
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Status Card */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">Status</div>
            <div className="mt-1">
              <ScanStatusBadge status={scan.status} />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">Progress</div>
            <div className="text-2xl font-bold mt-1">{scan.progress}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">Current Phase</div>
            <div className="text-sm font-medium mt-1 capitalize">
              {scan.current_phase?.replace("_", " ") ?? "-"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground">Findings</div>
            <div className="flex gap-1 mt-1 flex-wrap">
              {scan.findings_critical > 0 && (
                <Badge variant="critical">{scan.findings_critical}C</Badge>
              )}
              {scan.findings_high > 0 && (
                <Badge variant="high">{scan.findings_high}H</Badge>
              )}
              {scan.findings_medium > 0 && (
                <Badge variant="medium">{scan.findings_medium}M</Badge>
              )}
              {scan.findings_low > 0 && (
                <Badge variant="low">{scan.findings_low}L</Badge>
              )}
              {scan.findings_info > 0 && (
                <Badge variant="info">{scan.findings_info}I</Badge>
              )}
              {scan.findings_critical +
                scan.findings_high +
                scan.findings_medium +
                scan.findings_low +
                scan.findings_info ===
                0 && <span className="text-sm text-muted-foreground">-</span>}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b pb-2">
        {(
          [
            { key: "progress", label: "Live Progress" },
            { key: "findings", label: "Findings" },
            { key: "report", label: "Report" },
          ] as const
        ).map((tab) => (
          <Button
            key={tab.key}
            variant={activeTab === tab.key ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "progress" && (
        <ScanProgress
          scanId={scanId}
          phases={scan.phases ?? []}
          status={scan.status}
          progress={scan.progress}
          currentPhase={scan.current_phase}
        />
      )}

      {activeTab === "findings" && (
        <Card>
          <CardHeader>
            <CardTitle>Findings</CardTitle>
            <CardDescription>
              Vulnerabilities discovered during the scan
            </CardDescription>
          </CardHeader>
          <CardContent>
            {findings.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                {scan.status === "completed"
                  ? "No findings detected — your target appears secure!"
                  : "Findings will appear here once the scan completes."}
              </div>
            ) : (
              <FindingsTable findings={findings} />
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === "report" && (
        <Card>
          <CardHeader>
            <CardTitle>AI Analysis Report</CardTitle>
            <CardDescription>
              Claude AI-generated security assessment
            </CardDescription>
          </CardHeader>
          <CardContent>
            {scan.status !== "completed" ? (
              <div className="text-center py-8 text-muted-foreground">
                Report will be available after scan and AI analysis complete.
              </div>
            ) : report ? (
              <div className="space-y-6">
                {/* Executive Summary */}
                <div>
                  <h3 className="text-lg font-semibold mb-2">
                    Executive Summary
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {report.executive_summary}
                  </p>
                </div>

                {/* Scores */}
                {report.category_scores && (
                  <div>
                    <h3 className="text-lg font-semibold mb-3">
                      Security Scores
                    </h3>
                    <div className="grid gap-3 md:grid-cols-3">
                      {report.category_scores.map((score: any) => (
                        <div
                          key={score.category}
                          className="rounded-lg border p-4"
                        >
                          <div className="text-sm text-muted-foreground">
                            {score.category}
                          </div>
                          <div className="text-3xl font-bold mt-1">
                            {score.score}
                            <span className="text-sm font-normal text-muted-foreground">
                              /100
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Remediation Roadmap */}
                {report.remediation_roadmap && (
                  <div>
                    <h3 className="text-lg font-semibold mb-2">
                      Remediation Roadmap
                    </h3>
                    <div className="space-y-3">
                      {report.remediation_roadmap.map(
                        (item: any, idx: number) => (
                          <div
                            key={idx}
                            className="flex gap-4 rounded-lg border p-4"
                          >
                            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-medium">
                              {idx + 1}
                            </div>
                            <div>
                              <p className="font-medium">{item.action}</p>
                              <p className="text-sm text-muted-foreground">
                                Priority: {item.priority} &bull; Est:{" "}
                                {item.estimated_time}
                              </p>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                Loading report...
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Share Link */}
      {scan.share_token && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Share2 className="h-4 w-4" />
              Share Link
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <code className="flex-1 rounded border bg-muted/30 px-3 py-2 text-sm font-mono">
                {typeof window !== "undefined"
                  ? `${window.location.origin}/shared/${scan.share_token}`
                  : `/shared/${scan.share_token}`}
              </code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(
                    `${window.location.origin}/shared/${scan.share_token}`
                  );
                  toast.success("Link copied!");
                }}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ScanStatusBadge({ status }: { status: string }) {
  const config: Record<string, { className: string; icon: React.ReactNode }> = {
    completed: {
      className: "text-green-500 border-green-500",
      icon: <CheckCircle className="mr-1 h-3 w-3" />,
    },
    running: {
      className: "text-blue-500 border-blue-500",
      icon: <Activity className="mr-1 h-3 w-3 animate-pulse" />,
    },
    pending: {
      className: "text-yellow-500 border-yellow-500",
      icon: <Clock className="mr-1 h-3 w-3" />,
    },
    analyzing: {
      className: "text-purple-500 border-purple-500",
      icon: <Activity className="mr-1 h-3 w-3 animate-pulse" />,
    },
    failed: {
      className: "text-red-500 border-red-500",
      icon: <AlertTriangle className="mr-1 h-3 w-3" />,
    },
  };

  const c = config[status] ?? { className: "", icon: <Clock className="mr-1 h-3 w-3" /> };

  return (
    <Badge variant="outline" className={`flex items-center w-fit ${c.className}`}>
      {c.icon}
      {status.replace("_", " ")}
    </Badge>
  );
}
