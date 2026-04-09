"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi as api } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  Shield,
  Plus,
  CheckCircle,
  Activity,
  Clock,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";

export default function ScansPage() {
  const { data: scansData, isLoading } = useQuery({
    queryKey: ["scans"],
    queryFn: () => api.listScans(1, 50),
  });

  const scans = scansData?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Scans</h1>
          <p className="text-muted-foreground">
            Manage and monitor your penetration tests
          </p>
        </div>
        <Link href="/scans/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Scan
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">
          Loading scans...
        </div>
      ) : scans.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Shield className="h-12 w-12 mx-auto mb-4 opacity-30" />
            <p className="text-muted-foreground mb-4">
              No scans yet. Start your first penetration test!
            </p>
            <Link href="/scans/new">
              <Button>Start Scan</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {scans.map((scan: any) => (
            <Link key={scan.id} href={`/scans/${scan.id}`}>
              <Card className="hover:bg-muted/30 transition-colors cursor-pointer mb-3">
                <CardContent className="flex items-center justify-between p-6">
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                      <Shield className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">
                        {scan.scan_type.replace("_", " ")} scan
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Created{" "}
                        {new Date(scan.created_at).toLocaleDateString()} at{" "}
                        {new Date(scan.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    {scan.status === "completed" && (
                      <div className="flex gap-2 text-xs">
                        {scan.findings_critical > 0 && (
                          <Badge variant="critical">
                            {scan.findings_critical} Critical
                          </Badge>
                        )}
                        {scan.findings_high > 0 && (
                          <Badge variant="high">
                            {scan.findings_high} High
                          </Badge>
                        )}
                        {scan.findings_medium > 0 && (
                          <Badge variant="medium">
                            {scan.findings_medium} Medium
                          </Badge>
                        )}
                      </div>
                    )}

                    <StatusBadge status={scan.status} />

                    {scan.progress > 0 && scan.status === "running" && (
                      <span className="text-sm text-muted-foreground">
                        {scan.progress}%
                      </span>
                    )}

                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { className: string; icon: React.ReactNode; label: string }> = {
    completed: {
      className: "text-green-500 border-green-500",
      icon: <CheckCircle className="mr-1 h-3 w-3" />,
      label: "Completed",
    },
    running: {
      className: "text-blue-500 border-blue-500",
      icon: <Activity className="mr-1 h-3 w-3 animate-pulse" />,
      label: "Running",
    },
    pending: {
      className: "text-yellow-500 border-yellow-500",
      icon: <Clock className="mr-1 h-3 w-3" />,
      label: "Wachtend",
    },
    analyzing: {
      className: "text-purple-500 border-purple-500",
      icon: <Activity className="mr-1 h-3 w-3 animate-pulse" />,
      label: "Analyzing",
    },
    failed: {
      className: "text-red-500 border-red-500",
      icon: <AlertTriangle className="mr-1 h-3 w-3" />,
      label: "Failed",
    },
    cancelled: {
      className: "text-gray-500 border-gray-500",
      icon: <AlertTriangle className="mr-1 h-3 w-3" />,
      label: "Cancelled",
    },
  };

  const c = config[status] ?? {
    className: "",
    icon: <Clock className="mr-1 h-3 w-3" />,
    label: status,
  };

  return (
    <Badge variant="outline" className={`flex items-center ${c.className}`}>
      {c.icon}
      {c.label}
    </Badge>
  );
}
