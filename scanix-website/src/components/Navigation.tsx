"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, ArrowRight } from "lucide-react";
import { Link, usePathname, useRouter } from "@/lib/navigation";
import { locales } from "@/lib/i18n";

function Logo() {
  return (
    <Link href="/" className="font-display text-[19px] font-bold tracking-tight">
      <span className="text-cyan">Scan</span>
      <span className="text-ink">ix</span>
    </Link>
  );
}

function LanguageSwitcher() {
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="flex items-center gap-1 rounded-lg border border-grid bg-card/60 p-0.5">
      {locales.map((l) => (
        <button
          key={l}
          onClick={() => router.replace(pathname, { locale: l })}
          className={`rounded-md px-2 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors ${
            l === locale ? "bg-cyan/15 text-cyan" : "text-ink-muted hover:text-ink"
          }`}
          aria-current={l === locale ? "true" : undefined}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

export function Navigation() {
  const t = useTranslations("nav");
  const [open, setOpen] = useState(false);

  const links = [
    { href: "/#demo", label: "Demo" },
    { href: "/hoe-het-werkt", label: t("how") },
    { href: "/wat-we-testen", label: t("what") },
    { href: "/agent", label: t("agent") },
    { href: "/prijzen", label: t("pricing") },
    { href: "/contact", label: t("contact") },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-grid/70 bg-bg/80 backdrop-blur-md">
      <nav className="mx-auto flex max-w-content items-center justify-between px-5 py-3.5 md:px-8">
        <Logo />

        <div className="hidden items-center gap-8 lg:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-[14px] text-ink-muted transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 lg:flex">
          <LanguageSwitcher />
          <Link
            href="/login"
            className="text-[14px] font-medium text-ink-muted transition-colors hover:text-cyan"
          >
            {t("login")}
          </Link>
          <Link
            href="/contact"
            className="inline-flex items-center gap-1.5 rounded-lg bg-cyan px-4 py-2 text-[13px] font-semibold text-bg transition-all hover:shadow-glow-cyan active:scale-[0.98]"
          >
            {t("cta")}
            <ArrowRight className="h-4 w-4" strokeWidth={2} />
          </Link>
        </div>

        <button
          className="text-ink lg:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Menu"
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
            className="overflow-hidden border-t border-grid bg-bg-secondary lg:hidden"
          >
            <div className="flex flex-col gap-1 px-5 py-4">
              {links.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="rounded-md px-3 py-2.5 text-[15px] text-ink-muted transition-colors hover:bg-card hover:text-ink"
                >
                  {l.label}
                </Link>
              ))}
              <div className="mt-2 flex items-center justify-between border-t border-grid pt-4">
                <LanguageSwitcher />
                <Link href="/login" onClick={() => setOpen(false)} className="text-[14px] font-medium text-cyan">
                  {t("login")}
                </Link>
              </div>
              <Link
                href="/contact"
                onClick={() => setOpen(false)}
                className="mt-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-cyan px-4 py-2.5 text-[14px] font-semibold text-bg"
              >
                {t("cta")}
                <ArrowRight className="h-4 w-4" strokeWidth={2} />
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
