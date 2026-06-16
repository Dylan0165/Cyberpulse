import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { PageFrame } from "@/components/PageFrame";
import { PageHeader } from "@/components/PageHeader";
import { Pricing } from "@/components/Pricing";

export async function generateMetadata({
  params: { locale },
}: {
  params: { locale: string };
}): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "nav" });
  const m = await getTranslations({ locale, namespace: "meta" });
  return { title: `${t("pricing")} — Scanix`, description: m("description") };
}

export default async function Page({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "nav" });
  return (
    <PageFrame>
      <PageHeader title={t("pricing")} />
      <Pricing />
    </PageFrame>
  );
}
