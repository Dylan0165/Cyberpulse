import { getTranslations, setRequestLocale } from "next-intl/server";
import { ArrowLeft } from "lucide-react";
import { Link } from "@/lib/navigation";

export default async function PrivacyPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  const t = await getTranslations("privacy");

  const sections = [
    { title: t("s1Title"), body: t("s1Body") },
    { title: t("s2Title"), body: t("s2Body") },
    { title: t("s3Title"), body: t("s3Body") },
    { title: t("s4Title"), body: t("s4Body") },
    { title: t("s5Title"), body: t("s5Body") },
  ];

  return (
    <main className="relative mx-auto max-w-3xl px-5 py-16 md:px-8">
      <Link href="/" className="inline-flex items-center gap-1.5 text-[13px] text-ink-muted transition-colors hover:text-cyan">
        <ArrowLeft className="h-4 w-4" strokeWidth={2} />
        {t("back")}
      </Link>

      <div className="mt-6 flex items-baseline gap-3">
        <span className="font-display text-lg font-bold">
          <span className="text-cyan">Scan</span>
          <span className="text-ink">ix</span>
        </span>
      </div>

      <h1 className="mt-4 font-display text-3xl font-bold tracking-tight text-ink">{t("title")}</h1>
      <p className="mt-2 text-[13px] text-ink-muted">{t("updated")}</p>

      <div className="mt-10 space-y-8">
        {sections.map((s) => (
          <section key={s.title}>
            <h2 className="font-display text-[17px] font-semibold text-ink">{s.title}</h2>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">{s.body}</p>
          </section>
        ))}
      </div>
    </main>
  );
}
