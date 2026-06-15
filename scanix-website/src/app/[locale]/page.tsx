import { setRequestLocale } from "next-intl/server";
import { Navigation } from "@/components/Navigation";
import { Hero } from "@/components/Hero";
import { Problem } from "@/components/Problem";
import { HowItWorks } from "@/components/HowItWorks";
import { WhatWeTest } from "@/components/WhatWeTest";
import { Pricing } from "@/components/Pricing";
import { Trust } from "@/components/Trust";
import { Contact } from "@/components/Contact";
import { Footer } from "@/components/Footer";

export default function LandingPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  return (
    <main className="relative overflow-hidden">
      <Navigation />
      <Hero />
      <Problem />
      <HowItWorks />
      <WhatWeTest />
      <Pricing />
      <Trust />
      <Contact />
      <Footer />
    </main>
  );
}
