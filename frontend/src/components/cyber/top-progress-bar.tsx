"use client";

import { AnimatePresence, motion } from "framer-motion";

/**
 * Thin fixed progress bar at the very top of the viewport — GitHub/Linear style.
 * Shown while a scan is running; animates toward the given progress (capped ~92%
 * while active so it never looks "done" early), then to 100% and fades out.
 */
export function TopProgressBar({
  active,
  progress,
  complete,
}: {
  active: boolean;
  progress: number;       // 0-100
  complete?: boolean;
}) {
  const show = active || complete;
  const width = complete ? 100 : Math.min(Math.max(progress, 4), 92);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          key="top-progress"
          className="fixed left-0 top-0 z-[9999] h-[2px]"
          style={{ background: "var(--accent-cyan)" }}
          initial={{ width: "0%", opacity: 1 }}
          animate={{ width: `${width}%`, opacity: complete ? 0 : 1 }}
          exit={{ opacity: 0 }}
          transition={{
            width: { duration: 0.6, ease: "easeOut" },
            opacity: { duration: 0.3, delay: complete ? 0.3 : 0 },
          }}
        />
      )}
    </AnimatePresence>
  );
}
