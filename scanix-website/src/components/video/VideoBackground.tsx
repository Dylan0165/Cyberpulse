"use client";

import { useState } from "react";

type VideoBackgroundProps = {
  src: string;
  poster?: string;
  className?: string;
  overlayClassName?: string;
};

/**
 * Reusable full-bleed background video. Fades in once the browser can render a
 * frame; on any load/decode error it hides the video and shows a gradient
 * fallback so the section never renders empty. Everything is pointer-events-none
 * so it sits purely behind real content. preload="none" keeps it off the
 * critical path until the browser decides to fetch it.
 */
export function VideoBackground({
  src,
  poster,
  className,
  overlayClassName,
}: VideoBackgroundProps) {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className ?? ""}`}
    >
      {failed ? (
        <div className="absolute inset-0 bg-gradient-to-b from-bg via-bg-secondary to-bg" />
      ) : (
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="none"
          poster={poster}
          onCanPlay={() => setReady(true)}
          onLoadedData={() => setReady(true)}
          onError={() => setFailed(true)}
          className={`pointer-events-none absolute inset-0 h-full w-full object-cover transition-opacity duration-[1500ms] ${
            ready ? "opacity-100" : "opacity-0"
          }`}
        >
          <source src={src} type="video/mp4" />
        </video>
      )}
      <div
        className={`pointer-events-none absolute inset-0 ${
          overlayClassName ?? "bg-black/60"
        }`}
      />
    </div>
  );
}
