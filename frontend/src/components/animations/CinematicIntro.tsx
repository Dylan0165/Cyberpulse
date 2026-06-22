"use client";

import { useEffect, useState } from "react";
import { usePrefersReducedMotion } from "@/hooks/useAnimation";

const STORAGE_KEY = "scanix_hasSeenIntro";

type Phase = "in" | "hold" | "out" | "done";

export default function CinematicIntro({ onDone }: { onDone?: () => void }) {
  const reduced = usePrefersReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [phase, setPhase] = useState<Phase>("in");
  const [videoOk, setVideoOk] = useState(true);

  // Decide visibility on the client only (sessionStorage + reduced motion).
  useEffect(() => {
    if (typeof window === "undefined") return;
    let seen = false;
    try {
      seen = window.sessionStorage.getItem(STORAGE_KEY) !== null;
    } catch {
      seen = false;
    }
    if (seen || reduced) {
      try {
        window.sessionStorage.setItem(STORAGE_KEY, "1");
      } catch {
        /* ignore */
      }
      onDone?.();
      return;
    }
    setMounted(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reduced]);

  // Drive the timeline once mounted.
  useEffect(() => {
    if (!mounted) return;
    const holdT = window.setTimeout(() => setPhase("hold"), 600);
    const outT = window.setTimeout(() => setPhase("out"), 1400);
    const doneT = window.setTimeout(() => {
      setPhase("done");
      try {
        window.sessionStorage.setItem(STORAGE_KEY, "1");
      } catch {
        /* ignore */
      }
      setMounted(false);
      onDone?.();
    }, 2000);
    return () => {
      window.clearTimeout(holdT);
      window.clearTimeout(outT);
      window.clearTimeout(doneT);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted]);

  if (!mounted || phase === "done") return null;

  return (
    <div
      className="sxd-intro-overlay"
      data-out={phase === "out" ? "1" : "0"}
      aria-hidden="true"
    >
      <style>{`
        .sxd-intro-overlay {
          position: fixed;
          inset: 0;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #000;
          overflow: hidden;
          opacity: 1;
          transition: opacity 0.6s ease;
        }
        .sxd-intro-overlay[data-out="1"] {
          opacity: 0;
        }
        .sxd-intro-video {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
          opacity: 0.35;
        }
        .sxd-intro-wordmark {
          position: relative;
          z-index: 1;
          font-size: clamp(2.5rem, 9vw, 6rem);
          font-weight: 800;
          letter-spacing: -0.03em;
          opacity: 0;
          transform: scale(0.96);
          animation: sxd-intro-fade-in 0.6s ease forwards;
        }
        @keyframes sxd-intro-fade-in {
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
      `}</style>
      {videoOk && (
        <video
          className="sxd-intro-video"
          src="/videos/intro.mp4"
          autoPlay
          muted
          playsInline
          preload="none"
          onError={() => setVideoOk(false)}
        />
      )}
      <div className="sxd-intro-wordmark">
        <span style={{ color: "#06b6d4" }}>Scan</span>
        <span style={{ color: "#ffffff" }}>ix</span>
      </div>
    </div>
  );
}
