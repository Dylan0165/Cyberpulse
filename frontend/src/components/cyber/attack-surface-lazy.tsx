"use client";

import dynamic from "next/dynamic";
import { Boxes } from "lucide-react";
import type { SurfaceNode } from "./attack-surface";

const AttackSurface = dynamic(() => import("./attack-surface"), {
  ssr: false,
  loading: () => <SurfaceFallback />,
});

function hasWebGL(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl") || c.getContext("experimental-webgl"));
  } catch {
    return false;
  }
}

function SurfaceFallback({ nodes }: { nodes?: SurfaceNode[] }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-4">
      <Boxes className="h-7 w-7 text-cyan" />
      {nodes && nodes.length > 0 ? (
        <div className="flex flex-wrap justify-center gap-2">
          {nodes.map((n) => (
            <span key={n.id} className="rounded border border-grid bg-card2 px-2 py-1 font-mono text-[10px] text-ink-muted">
              :{n.port} {n.service}
            </span>
          ))}
        </div>
      ) : (
        <span className="font-mono text-[11px] uppercase tracking-wider text-ink-muted">no open ports mapped</span>
      )}
    </div>
  );
}

export function AttackSurfacePanel({
  nodes,
  onSelect,
}: {
  nodes: SurfaceNode[];
  onSelect?: (n: SurfaceNode) => void;
}) {
  const webgl = typeof window !== "undefined" ? hasWebGL() : true;
  return (
    <div
      className="relative h-[340px] w-full overflow-hidden rounded-lg border border-grid"
      style={{ background: "radial-gradient(ellipse at center, #05101a 0%, #020408 100%)" }}
    >
      <div className="absolute left-4 top-3 z-10 font-mono text-[10px] uppercase tracking-widest text-ink-muted">
        attack surface · {nodes.length} nodes
      </div>
      {webgl && nodes.length > 0 ? (
        <AttackSurface nodes={nodes} onSelect={onSelect} />
      ) : (
        <SurfaceFallback nodes={nodes} />
      )}
    </div>
  );
}
