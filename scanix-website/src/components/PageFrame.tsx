"use client";

import { motion } from "framer-motion";
import { Navigation } from "./Navigation";
import { Footer } from "./Footer";

/**
 * Shared chrome for every routed page: sticky nav, a fade-in main region
 * (the page transition), and the footer.
 */
export function PageFrame({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Navigation />
      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        // overflow-x-clip (not overflow-hidden) prevents horizontal scroll
        // WITHOUT creating a scroll container — otherwise position:sticky on
        // child sections (e.g. StickyScrollScene's 300vh pin) silently breaks,
        // leaving a large empty gap mid-page.
        className="relative min-h-[60vh] overflow-x-clip"
      >
        {children}
      </motion.main>
      <Footer />
    </>
  );
}
