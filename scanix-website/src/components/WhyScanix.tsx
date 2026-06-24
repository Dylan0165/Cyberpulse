import { useTranslations } from "next-intl";
import { Zap, FileText, ShieldCheck } from "lucide-react";

/**
 * "Waarom Scanix" — three value props between the hero and the stats.
 * Static (no scroll/JS) so it always renders, anchoring the mid-page area.
 */
export function WhyScanix() {
  const t = useTranslations("whyScanix");

  const cols = [
    { icon: Zap, title: t("col1Title"), text: t("col1Text") },
    { icon: FileText, title: t("col2Title"), text: t("col2Text") },
    { icon: ShieldCheck, title: t("col3Title"), text: t("col3Text") },
  ];

  return (
    <section className="relative mx-auto max-w-content px-5 py-20 md:px-8 md:py-28">
      <div className="text-center">
        <h2 className="font-display text-3xl font-bold tracking-tight text-ink md:text-4xl">
          {t("title")}
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-[15px] text-ink-muted">{t("subtitle")}</p>
      </div>

      <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
        {cols.map((c) => (
          <div
            key={c.title}
            className="rounded-2xl border border-grid bg-card p-7 transition-colors hover:border-cyan/40"
          >
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl border border-cyan/30 bg-cyan/10">
              <c.icon className="h-6 w-6 text-cyan" strokeWidth={2} />
            </span>
            <h3 className="mt-5 font-display text-xl font-bold tracking-tight text-ink">{c.title}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-ink-muted">{c.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
