"use client";

import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";
import { Link } from "@/lib/navigation";
import { APP_URL } from "@/lib/appUrl";

export function Footer() {
  const t = useTranslations("footer");

  const pageLinks = [
    { href: "/hoe-het-werkt", label: t("how") },
    { href: "/wat-we-testen", label: t("what") },
    { href: "/prijzen", label: t("pricing") },
    { href: "/contact", label: t("contact") },
  ];

  return (
    <footer className="border-t border-grid">
      <div className="mx-auto grid max-w-content grid-cols-1 gap-8 px-5 py-12 md:grid-cols-3 md:px-8">
        {/* Left */}
        <div>
          <p className="font-display text-lg font-bold">
            <span className="text-cyan">Scan</span>
            <span className="text-ink">ix</span>
          </p>
          <p className="mt-3 text-[14px] text-ink-muted">{t("tagline")}</p>
          <p className="mt-2 text-xs text-ink-muted">{t("copyright")}</p>
        </div>

        {/* Center */}
        <nav className="flex flex-col gap-2.5">
          {pageLinks.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-[14px] text-ink-muted transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
          <Link
            href="/terms"
            className="text-[14px] text-ink-muted transition-colors hover:text-ink"
          >
            {t("terms")}
          </Link>
          <Link
            href="/privacy"
            className="text-[14px] text-ink-muted transition-colors hover:text-ink"
          >
            {t("privacy")}
          </Link>
        </nav>

        {/* Right */}
        <div className="flex flex-col items-start gap-3 md:items-end">
          <p className="font-mono text-[12px] text-ink-muted">NL · EN · FR · DE</p>
          <a
            href={APP_URL}
            className="inline-flex items-center gap-1.5 text-[14px] font-semibold text-cyan transition-colors hover:text-cyan/80"
          >
            {t("login")}
            <ArrowRight className="h-4 w-4" strokeWidth={2} />
          </a>
        </div>
      </div>
    </footer>
  );
}
