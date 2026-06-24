import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { PageFrame } from "@/components/PageFrame";
import { PageHeader } from "@/components/PageHeader";
import { AgentInfo } from "@/components/AgentInfo";

export async function generateMetadata({
  params: { locale },
}: {
  params: { locale: string };
}): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "agentPage" });
  return { title: `${t("title")} — Scanix`, description: t("subtitle") };
}

export default async function Page({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "agentPage" });
  return (
    <PageFrame>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <AgentInfo />
    </PageFrame>
  );
}
