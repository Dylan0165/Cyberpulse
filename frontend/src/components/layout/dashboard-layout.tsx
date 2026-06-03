"use client";

import { Sidebar } from "./sidebar";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[240px_1fr] h-screen bg-background">
      <Sidebar />
      <main className="overflow-auto p-8">
        {children}
      </main>
    </div>
  );
}
