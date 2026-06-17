import { setRequestLocale } from "next-intl/server";
import { PageFrame } from "@/components/PageFrame";
import { Hero } from "@/components/Hero";
import { Demo } from "@/components/Demo";
import { Problem } from "@/components/Problem";
import { DiscoverMore } from "@/components/DiscoverMore";

export default function LandingPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  return (
    <PageFrame>
      <Hero />
      <Demo />
      <Problem />
      <DiscoverMore />
    </PageFrame>
  );
}
