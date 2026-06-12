"use client";

import { useEffect, useRef, useState } from "react";
import { Copy, Check, Terminal as TerminalIcon } from "lucide-react";

export interface TermLine {
  text: string;
  kind?: "phase" | "success" | "error" | "warn" | "out" | "dim";
}

const KIND_CLASS: Record<string, string> = {
  phase: "term-phase",
  success: "term-success",
  error: "term-error",
  warn: "term-warn",
  out: "term-out",
  dim: "term-dim",
};

export function TerminalOutput({
  lines,
  complete = false,
  autoScroll = true,
}: {
  lines: TermLine[];
  complete?: boolean;
  autoScroll?: boolean;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (autoScroll) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines, autoScroll]);

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(lines.map((l) => l.text).join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  return (
    <div className="relative overflow-hidden rounded-lg border border-grid" style={{ background: "#000208" }}>
      {/* Scanline overlay */}
      <div className="scanlines" style={{ position: "absolute", zIndex: 3, opacity: 0.4 }} aria-hidden />

      {/* Header */}
      <div
        className="flex items-center justify-between border-b border-grid px-4 py-2"
        style={{ background: "rgba(5,13,20,0.8)" }}
      >
        <div className="flex items-center gap-2">
          <TerminalIcon className="h-3.5 w-3.5 text-cyan" />
          <span className="font-mono text-[11px] uppercase tracking-wider text-ink-muted">
            live output
          </span>
        </div>
        <button
          onClick={copyAll}
          className="flex items-center gap-1.5 rounded px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-ink-muted transition-colors hover:text-cyan"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? "copied" : "copy"}
        </button>
      </div>

      {/* Body */}
      <div className="terminal-output relative z-[2] max-h-[480px] min-h-[280px] overflow-y-auto px-4 py-3">
        {lines.length === 0 ? (
          <div className="term-dim terminal-cursor">awaiting scan output </div>
        ) : (
          lines.map((l, i) => (
            <div key={i} className={KIND_CLASS[l.kind ?? "out"]}>
              {l.text}
            </div>
          ))
        )}
        {complete && (
          <div
            className="mt-3 inline-block rounded border px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-widest"
            style={{
              color: "#00FF88",
              borderColor: "#00FF8855",
              background: "rgba(0,255,136,0.08)",
              boxShadow: "0 0 16px rgba(0,255,136,0.2)",
            }}
          >
            ✓ scan complete
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
