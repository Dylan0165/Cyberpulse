"use client";

import { Sidebar } from "./sidebar";
import { PageTransition } from "@/components/cyber/page-transition";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-app">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-[1500px] px-6 py-6 lg:px-8 lg:py-8">
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
    </div>
  );
}
