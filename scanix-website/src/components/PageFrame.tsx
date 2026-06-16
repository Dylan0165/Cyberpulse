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
        className="relative min-h-[60vh] overflow-hidden"
      >
        {children}
      </motion.main>
      <Footer />
    </>
  );
}
