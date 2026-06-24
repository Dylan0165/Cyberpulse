import { setRequestLocale } from "next-intl/server";
import { PageFrame } from "@/components/PageFrame";
import { Hero } from "@/components/Hero";
import { StickyScrollScene } from "@/components/video/StickyScrollScene";
import { Demo } from "@/components/Demo";
import { Problem } from "@/components/Problem";
import { DiscoverMore } from "@/components/DiscoverMore";
import { PricingPreview } from "@/components/PricingPreview";
import { CinematicCta } from "@/components/CinematicCta";

export default function LandingPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  return (
    <PageFrame>
      <Hero />
      <StickyScrollScene />
      <Demo />
      <Problem />
      <DiscoverMore />
      <PricingPreview />
      <CinematicCta />
    </PageFrame>
  );
}
