"use client";

import dynamic from "next/dynamic";
import { Globe } from "lucide-react";
import type { GlobeTarget } from "./network-globe";

const NetworkGlobe = dynamic(() => import("./network-globe"), {
  ssr: false,
  loading: () => <GlobeFallback />,
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

function GlobeFallback() {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="flex flex-col items-center gap-2 text-ink-muted">
        <Globe className="h-8 w-8 animate-pulse text-cyan" />
        <span className="font-mono text-[11px] uppercase tracking-wider">rendering network map…</span>
      </div>
    </div>
  );
}

export function NetworkGlobePanel({ targets }: { targets: GlobeTarget[] }) {
  const webgl = typeof window !== "undefined" ? hasWebGL() : true;
  return (
    <div
      className="relative h-[300px] w-full overflow-hidden rounded-lg border border-grid"
      style={{ background: "radial-gradient(ellipse at center, #05101a 0%, #020408 100%)" }}
    >
      <div className="absolute left-4 top-3 z-10 font-mono text-[10px] uppercase tracking-widest text-ink-muted">
        global target map
      </div>
      {webgl ? <NetworkGlobe targets={targets} /> : <GlobeFallback />}
    </div>
  );
}
