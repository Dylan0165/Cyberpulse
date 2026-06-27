import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { PageFrame } from "@/components/PageFrame";
import { PageHeader } from "@/components/PageHeader";
import { DemoScanRunner } from "@/components/DemoScanRunner";

export async function generateMetadata({
  params: { locale },
}: {
  params: { locale: string };
}): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "demoPage" });
  return { title: `${t("title")} — Scanix`, description: t("subtitle") };
}

export default async function Page({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "demoPage" });
  return (
    <PageFrame>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <section className="relative mx-auto max-w-content px-5 py-12 md:px-8 md:py-16">
        <DemoScanRunner />
      </section>
    </PageFrame>
  );
}
