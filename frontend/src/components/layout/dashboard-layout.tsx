"use client";

import { Sidebar, MobileNav } from "./sidebar";
import { HeaderBell } from "./header-bell";
import { CreditsBadge } from "./credits-badge";
import { LogoutButton } from "./logout-button";
import { PageTransition } from "@/components/cyber/page-transition";
import { TermsModal } from "@/components/cyber/terms-modal";
import { TrialBanner } from "@/components/cyber/trial-banner";
import CinematicIntro from "@/components/animations/CinematicIntro";
import AppBackgroundVideo from "@/components/animations/AppBackgroundVideo";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";
import { useAuth } from "@/contexts/auth-context";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, refresh } = useAuth();
  const mustAcceptTerms = user != null && user.terms_accepted === false;
  // Show onboarding once: terms first, then the wizard for users who haven't done it.
  const showOnboarding = user != null && !mustAcceptTerms && user.onboarding_completed === false;

  return (
    <div className="relative flex h-screen overflow-hidden bg-app">
      {/* Permanent, barely-there cinematic background (md+ / motion only) */}
      <AppBackgroundVideo />
      {/* Once-per-session cinematic intro (self-gates via sessionStorage + reduced-motion) */}
      <CinematicIntro />
      <Sidebar />
      <main className="relative z-10 flex-1 overflow-auto">
        {/* Slim top header bar */}
        <header className="flex h-14 items-center justify-end gap-3 border-b border-grid bg-panel px-6 lg:px-8">
          <CreditsBadge />
          <HeaderBell />
          <LogoutButton />
        </header>
        <div className="mx-auto max-w-[1500px] px-6 py-6 pb-20 lg:px-8 lg:py-8 md:pb-8">
          <TrialBanner />
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
      <MobileNav />
      {mustAcceptTerms && <TermsModal open onAccepted={refresh} />}
      {showOnboarding && <OnboardingWizard />}
    </div>
  );
}
