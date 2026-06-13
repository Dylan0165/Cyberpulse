"use client";

import { Sidebar, MobileNav } from "./sidebar";
import { HeaderBell } from "./header-bell";
import { PageTransition } from "@/components/cyber/page-transition";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-app">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {/* Slim top header bar */}
        <header className="flex h-14 items-center justify-end border-b border-grid bg-panel px-6 lg:px-8">
          <HeaderBell />
        </header>
        <div className="mx-auto max-w-[1500px] px-6 py-6 pb-20 lg:px-8 lg:py-8 md:pb-8">
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
      <MobileNav />
    </div>
  );
}
