"use client";

import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { useScanWebSocket } from "@/hooks/use-scan-websocket";
import { CheckCircle, Circle, Loader2, XCircle } from "lucide-react";

const PHASE_LABELS: Record<string, string> = {
  recon: "Reconnaissance",
  vulnerability: "Vulnerability Scanning",
  webapp: "Web Application Testing",
  network: "Network & Infrastructure",
  auth: "Authentication Testing",
  ssl: "SSL/TLS & Cryptography",
  cloud: "Cloud & Container Security",
  osint: "OSINT & Exposure",
};

interface ScanProgressProps {
  scanId: string;
  phases: string[];
  currentPhase: string | null;
  progress: number;
  status: string;
}

export function ScanProgress({ scanId, phases, currentPhase, progress, status }: ScanProgressProps) {
  const { events, connected } = useScanWebSocket(
    status === "running" || status === "analyzing" ? scanId : null
  );

  // Derive phase statuses from events
  const completedPhases = new Set<string>();
  const failedPhases = new Set<string>();
  let livePhase = currentPhase;

  for (const event of events) {
    if (event.type === "phase_complete" && event.phase) {
      completedPhases.add(event.phase);
    }
    if (event.type === "phase_error" && event.phase) {
      failedPhases.add(event.phase);
    }
    if (event.type === "phase_start" && event.phase) {
      livePhase = event.phase;
    }
  }

  const liveProgress = events.length > 0
    ? events[events.length - 1].progress ?? progress
    : progress;

  return (
    <div className="space-y-6">
      {/* Overall progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">Scan Progress</span>
          <span className="text-muted-foreground">{liveProgress}%</span>
        </div>
        <Progress value={liveProgress} />
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {connected && (
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
          )}
          {status === "analyzing" && (
            <Badge variant="secondary">AI Analysis in progress...</Badge>
          )}
        </div>
      </div>

      {/* Phase list */}
      <div className="space-y-2">
        {phases.map((phase) => {
          const isComplete = completedPhases.has(phase);
          const isFailed = failedPhases.has(phase);
          const isCurrent = phase === livePhase && !isComplete && !isFailed;

          return (
            <div
              key={phase}
              className="flex items-center gap-3 rounded-lg border p-3 transition-colors"
              style={{
                backgroundColor: isCurrent ? "hsl(var(--accent))" : undefined,
              }}
            >
              {isComplete ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : isFailed ? (
                <XCircle className="h-5 w-5 text-red-500" />
              ) : isCurrent ? (
                <Loader2 className="h-5 w-5 text-primary animate-spin" />
              ) : (
                <Circle className="h-5 w-5 text-muted-foreground" />
              )}
              <span className={isCurrent ? "font-medium" : "text-muted-foreground"}>
                {PHASE_LABELS[phase] || phase}
              </span>
            </div>
          );
        })}
      </div>

      {/* Live terminal output */}
      {(status === "running" || status === "analyzing") && events.length > 0 && (
        <div className="rounded-lg border bg-black p-4">
          <div className="mb-2 text-xs text-green-400 font-mono">Live Output</div>
          <div className="max-h-64 overflow-y-auto font-mono text-xs text-green-300 space-y-1">
            {events
              .filter((e) => e.type === "tool_output" || e.type === "tool_start" || e.type === "tool_complete")
              .slice(-50)
              .map((event, i) => (
                <div key={i}>
                  {event.type === "tool_start" && (
                    <span className="text-yellow-400">
                      [START] {event.phase}/{event.tool}
                    </span>
                  )}
                  {event.type === "tool_complete" && (
                    <span className="text-green-400">
                      [DONE] {event.phase}/{event.tool}
                    </span>
                  )}
                  {event.type === "tool_output" && (
                    <span className="text-gray-300">
                      {event.output?.substring(0, 200)}
                    </span>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
