"use client";

import { useTranslations } from "next-intl";
import { ChevronRight } from "lucide-react";
import { Link } from "@/lib/navigation";

/** Breadcrumb (Home → title) + large page heading. */
export function PageHeader({ title }: { title: string }) {
  const t = useTranslations("pages");
  return (
    <div className="mx-auto max-w-content px-5 pt-12 md:px-8 md:pt-16">
      <nav className="flex items-center gap-1.5 text-[13px] text-ink-muted">
        <Link href="/" className="transition-colors hover:text-cyan">
          {t("home")}
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-ink-muted/50" strokeWidth={2} />
        <span className="text-ink">{title}</span>
      </nav>
      <h1 className="mt-3 font-display text-4xl font-bold tracking-tight text-ink md:text-5xl">
        {title}
      </h1>
    </div>
  );
}
