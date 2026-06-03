"use client";

import { Sidebar } from "./sidebar";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[260px_1fr] h-screen bg-secondary overflow-hidden">
      <Sidebar />
      <main className="overflow-auto bg-secondary">
        <div className="min-h-full bg-background m-3 rounded-xl shadow-apple p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
