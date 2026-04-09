"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FindingsTable } from "@/components/scan/findings-table";
import { Shield, AlertTriangle } from "lucide-react";
import type { Finding } from "@/types";

export default function SharedReportPage() {
  const params = useParams();
  const token = params.token as string;
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
        const res = await fetch(`${apiUrl}/api/scans/shared/${token}`);
        if (!res.ok) {
          setError("Report not found or link expired");
          return;
        }
        const data = await res.json();
        setReport(data);
      } catch {
        setError("Failed to load report");
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground">
        Loading report...
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-destructive" />
            <p className="text-lg font-medium">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const findings: Finding[] = report?.findings ?? [];

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <span className="font-bold">AutoPentest AI — Shared Report</span>
        </div>
      </nav>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {report?.executive_summary && (
          <Card>
            <CardHeader>
              <CardTitle>Executive Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {report.executive_summary}
              </p>
            </CardContent>
          </Card>
        )}

        {report?.category_scores && (
          <div className="grid gap-4 md:grid-cols-3">
            {report.category_scores.map((score: any) => (
              <Card key={score.category}>
                <CardContent className="pt-6 text-center">
                  <div className="text-sm text-muted-foreground">
                    {score.category}
                  </div>
                  <div className="text-4xl font-bold mt-2">
                    {score.score}
                    <span className="text-sm font-normal text-muted-foreground">
                      /100
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {findings.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Findings</CardTitle>
              <CardDescription>
                {findings.length} vulnerabilities identified
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FindingsTable findings={findings} />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
