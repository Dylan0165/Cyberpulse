import { setRequestLocale } from "next-intl/server";
import { PageFrame } from "@/components/PageFrame";
import { Hero } from "@/components/Hero";
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
      <Problem />
      <DiscoverMore />
    </PageFrame>
  );
}
