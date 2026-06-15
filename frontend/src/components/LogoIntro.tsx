"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

// Logo intro overlay — plays the animated Scanix logo once per browser session.
// Video served from /public/logo-intro.mp4, static poster /public/logoCyber.png.
// TODO: optionally swap to the Higgsfield CDN URL when available.
// Job ID: da608e8b-235b-4ac2-a1dc-05cea5ea2fa2

const MAX_DURATION_MS = 6000; // hard cap — fade out after at most 6s
const SESSION_KEY = "intro_shown";

export default function LogoIntro() {
  // Start hidden; decide on mount (avoids SSR/hydration flash).
  const [show, setShow] = useState(false);
  const [showSkip, setShowSkip] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    let alreadyShown = false;
    try {
      alreadyShown = sessionStorage.getItem(SESSION_KEY) === "true";
    } catch {
      alreadyShown = false;
    }
    if (alreadyShown) return;

    setShow(true);
    try {
      sessionStorage.setItem(SESSION_KEY, "true");
    } catch {}

    // Hard cap so the overlay never gets stuck (e.g. video fails to fire 'ended')
    const capTimer = setTimeout(() => setShow(false), MAX_DURATION_MS);
    // Reveal the skip control after 1s so it doesn't flash immediately
    const skipTimer = setTimeout(() => setShowSkip(true), 1000);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShow(false);
    };
    window.addEventListener("keydown", onKey);

    return () => {
      clearTimeout(capTimer);
      clearTimeout(skipTimer);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Scanix intro animatie"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
          className="fixed inset-0 flex items-center justify-center"
          style={{ zIndex: 9999, background: "#020408" }}
        >
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            poster="/logoCyber.png"
            onEnded={() => setShow(false)}
            className="w-[80vw] max-w-[480px] select-none"
            style={{ filter: "drop-shadow(0 0 40px rgba(0,212,255,0.25))" }}
          >
            <source src="/logo-intro.mp4" type="video/mp4" />
          </video>

          {showSkip && (
            <button
              onClick={() => setShow(false)}
              className="absolute bottom-6 right-6 font-mono text-[12px] transition-opacity hover:opacity-70"
              style={{ color: "#4A6880" }}
            >
              Overslaan →
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
