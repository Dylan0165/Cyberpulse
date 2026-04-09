"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Settings, Key, Server } from "lucide-react";
import { toolsApi } from "@/lib/api";

export default function SettingsPage() {
  const [toolStatus, setToolStatus] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    toolsApi
      .check()
      .then((r) => setToolStatus(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const installedCount = Object.values(toolStatus).filter(Boolean).length;
  const totalCount = Object.keys(toolStatus).length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[18px] font-bold tracking-[0.05em]">Instellingen</h1>
        <p className="text-muted-foreground text-[12px]">
          Systeem- en engine-instellingen
        </p>
      </div>

      {/* Engine Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">
            <Server className="h-4 w-4" />
            Engine Status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="inline-block h-[6px] w-[6px] rounded-full bg-green-500" />
            <span className="text-[13px]">CyberPulse Engine � lokaal actief</span>
          </div>
          <div className="text-[12px] text-muted-foreground">
            Backend: <code className="bg-secondary px-1">http://localhost:8000</code>
          </div>
        </CardContent>
      </Card>

      {/* Kali Tools */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">
            <Key className="h-4 w-4" />
            Kali Tools
          </CardTitle>
          <CardDescription>
            {loading ? "Controleren..." : `${installedCount} / ${totalCount} gevonden op dit systeem`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!loading && totalCount > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-[1px] bg-border">
              {Object.entries(toolStatus)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([name, available]) => (
                  <div
                    key={name}
                    className={`bg-card px-3 py-2 text-[11px] font-mono ${
                      available ? "" : "opacity-40"
                    }`}
                  >
                    {available ? "?" : "?"} {name}
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[11px] uppercase tracking-[0.1em] text-muted-foreground font-normal">
            <Settings className="h-4 w-4" />
            API Informatie
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-secondary p-4 font-mono text-[12px] leading-[1.8]">
            <div>GET  /api/scans          � Alle scans</div>
            <div>POST /api/scans          � Nieuwe scan</div>
            <div>GET  /api/tools/available � Beschikbare tools</div>
            <div>POST /api/tools/scan     � Tool-scan starten</div>
            <div>GET  /api/reports/:id/pdf � PDF rapport</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
