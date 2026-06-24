"use client";

import { useEffect, useState } from "react";
import { usePrefersReducedMotion } from "@/hooks/useAnimation";

/**
 * Permanent, barely-there cinematic background for the dashboard shell.
 * animatie1 loops at 0.06 opacity behind all content so the app always feels
 * "alive". Skipped entirely on reduced-motion and on mobile (< 768px) per the
 * performance rules — the element is not even mounted, so nothing is fetched.
 *
 * Rendered as the first child of the (now relative) shell container and
 * positioned absolute inset-0 / z-0, so it paints above the opaque shell
 * background but beneath the sidebar and page content.
 */
export default function AppBackgroundVideo() {
  const reduced = usePrefersReducedMotion();
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (reduced || typeof window === "undefined" || !window.matchMedia) {
      setShow(false);
      return;
    }
    const mq = window.matchMedia("(min-width: 768px)");
    setShow(mq.matches);
    const handler = (e: MediaQueryListEvent) => setShow(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [reduced]);

  if (!show) return null;

  return (
    <video
      src="/videos/animatie1.mp4"
      autoPlay
      muted
      loop
      playsInline
      preload="none"
      aria-hidden="true"
      tabIndex={-1}
      className="pointer-events-none absolute inset-0 z-0 h-full w-full object-cover"
      style={{ opacity: 0.06 }}
    />
  );
}
