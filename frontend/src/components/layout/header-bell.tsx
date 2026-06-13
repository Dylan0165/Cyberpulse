"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, CheckCheck, CheckCircle2 } from "lucide-react";

type Notification = {
  id: string;
  title?: string;
  message?: string;
  scan_id?: string;
  is_read?: boolean;
  created_at?: string;
};

function timeAgo(date?: string): string {
  if (!date) return "";
  const diff = Date.now() - new Date(date).getTime();
  if (Number.isNaN(diff)) return "";
  const min = Math.floor(diff / 60000);
  if (min < 1) return "zojuist";
  if (min < 60) return `${min} min geleden`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs} uur geleden`;
  const days = Math.floor(hrs / 24);
  return `${days} dag${days > 1 ? "en" : ""} geleden`;
}

export function HeaderBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notification[]>([]);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Poll notifications every 30s — graceful, never throws.
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch("/api/notifications");
        if (!res.ok) return;
        const data: any = await res.json();
        const list: Notification[] = Array.isArray(data)
          ? data
          : Array.isArray(data?.items)
          ? data.items
          : [];
        if (!cancelled) setItems(list);
      } catch {
        /* graceful — keep current state, show empty */
      }
    }

    load();
    const interval = setInterval(load, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Close on outside click.
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const unread = items.filter((n) => !n.is_read).length;

  async function markRead(id: string) {
    setItems((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
    try {
      await fetch(`/api/notifications/${id}/read`, { method: "POST" });
    } catch {
      /* best-effort */
    }
  }

  async function markAllRead() {
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try {
      await fetch("/api/notifications/read-all", { method: "POST" });
    } catch {
      /* best-effort */
    }
  }

  function handleItemClick(n: Notification) {
    if (!n.is_read) markRead(n.id);
    if (n.scan_id) {
      setOpen(false);
      router.push(`/scans/${n.scan_id}`);
    }
  }

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        aria-label="Meldingen"
        onClick={() => setOpen((v) => !v)}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg border border-grid bg-card2 text-ink-muted transition-colors hover:border-cyan/40 hover:text-cyan"
      >
        <Bell className="h-[18px] w-[18px]" />
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-neon-red px-1 font-mono text-[10px] font-bold leading-none text-white shadow-[0_0_8px_#FF2D55]">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.16 }}
            className="absolute right-0 top-12 z-50 w-80 overflow-hidden rounded-lg border border-grid bg-card2 shadow-glow-cyan"
          >
            <div className="flex items-center justify-between border-b border-grid px-4 py-3">
              <span className="font-display text-[13px] font-semibold tracking-[0.06em] text-ink">
                Meldingen
              </span>
              <button
                type="button"
                onClick={markAllRead}
                className="inline-flex items-center gap-1.5 text-[11px] font-medium text-cyan transition-opacity hover:opacity-70"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Alles gelezen
              </button>
            </div>

            <div className="max-h-80 overflow-auto">
              {items.length === 0 ? (
                <div className="px-4 py-8 text-center font-mono text-[12px] text-ink-muted">
                  Geen nieuwe meldingen
                </div>
              ) : (
                <ul>
                  {items.map((n) => (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => handleItemClick(n)}
                        className={`flex w-full items-start gap-3 border-b border-grid px-4 py-3 text-left transition-colors hover:bg-panel ${
                          !n.is_read ? "border-l-2 border-l-cyan" : ""
                        }`}
                      >
                        <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-neon-green" />
                        <div className="min-w-0 flex-1">
                          {n.title && (
                            <div className="truncate text-[13px] font-medium text-ink">
                              {n.title}
                            </div>
                          )}
                          {n.message && (
                            <div className="mt-0.5 line-clamp-2 text-[12px] text-ink-muted">
                              {n.message}
                            </div>
                          )}
                          {n.created_at && (
                            <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                              {timeAgo(n.created_at)}
                            </div>
                          )}
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
