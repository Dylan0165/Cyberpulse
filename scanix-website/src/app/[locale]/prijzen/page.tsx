import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { PageFrame } from "@/components/PageFrame";
import { PageHeader } from "@/components/PageHeader";
import { Pricing } from "@/components/Pricing";
import { LiveDemoVideo } from "@/components/video/LiveDemoVideo";

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
      <div className="mx-auto grid max-w-content gap-8 px-5 md:px-8 lg:grid-cols-[minmax(0,360px)_1fr] lg:items-start lg:gap-10">
        <div className="pt-4 lg:pt-20">
          <LiveDemoVideo src="/videos/demo1.mp4" label="LIVE DEMO" />
        </div>
        <div>
          <Pricing />
        </div>
      </div>
    </PageFrame>
  );
}
