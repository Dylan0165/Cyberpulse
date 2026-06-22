"use client";

type LiveDemoVideoProps = {
  src: string;
  poster?: string;
  label: string;
};

/**
 * Floating "live preview" demo. Sticky on lg+ so it follows the pricing scroll,
 * static on mobile. preload="none" keeps it cheap until the browser fetches it.
 */
export function LiveDemoVideo({ src, poster, label }: LiveDemoVideoProps) {
  return (
    <div className="static lg:sticky lg:top-24">
      <div className="relative overflow-hidden rounded-2xl border-2 border-cyan-500/40 animate-pulse-border">
        <span className="absolute left-3 top-3 z-10 rounded-md bg-orange-500 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-white">
          {label}
        </span>
        <video
          src={src}
          poster={poster}
          autoPlay
          muted
          loop
          playsInline
          preload="none"
          className="block aspect-video w-full object-cover"
        />
      </div>
      <style>{`
        @keyframes sxw-demo-pulse {
          0%, 100% { border-color: rgba(0, 180, 216, 0.4); }
          50% { border-color: rgba(0, 180, 216, 0.9); }
        }
        .animate-pulse-border {
          animation: sxw-demo-pulse 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
