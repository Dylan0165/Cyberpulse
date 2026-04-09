'use client';

import { useEffect, useState, useCallback } from 'react';
import { notificationsApi } from '@/lib/api';

const SEV_ICONS: Record<string, string> = {
  critical: '🔴', high: '🟠', medium: '🟡', low: '🟢', info: '🔵',
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const [data, { count }] = await Promise.all([
      notificationsApi.list(50),
      notificationsApi.unreadCount(),
    ]);
    setNotifications(data);
    setUnread(count);
  }, []);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, [load]);

  async function markRead(id: string) {
    await notificationsApi.markRead(id);
    await load();
  }

  async function readAll() {
    await notificationsApi.markAllRead();
    await load();
  }

  async function clearAll() {
    if (!confirm('Alle meldingen verwijderen?')) return;
    await notificationsApi.clear();
    await load();
  }

  function fmtTs(ts: string) {
    try {
      const d = new Date(ts);
      const diffMin = Math.floor((Date.now() - d.getTime()) / 60000);
      if (diffMin < 1) return 'Zojuist';
      if (diffMin < 60) return `${diffMin} min geleden`;
      if (diffMin < 1440) return `${Math.floor(diffMin / 60)} uur geleden`;
      return d.toLocaleDateString('nl-NL');
    } catch { return ts; }
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Meldingen</h1>
          {unread > 0 && (
            <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-sm">{unread}</span>
          )}
        </div>
        <div className="flex gap-2">
          {unread > 0 && (
            <button onClick={readAll} className="text-xs border border-gray-700 text-gray-400 px-3 py-1.5 hover:border-cyan-400 hover:text-white">
              Alles gelezen
            </button>
          )}
          {notifications.length > 0 && (
            <button onClick={clearAll} className="text-xs border border-red-500/50 text-red-400 px-3 py-1.5 hover:bg-red-500/10">
              Wis alles
            </button>
          )}
        </div>
      </div>

      {loading && <div className="text-gray-400 text-center py-8">Laden…</div>}

      {!loading && notifications.length === 0 && (
        <div className="text-gray-400 text-center py-12">
          Geen meldingen. Meldingen verschijnen hier na scans.
        </div>
      )}

      {!loading && notifications.length > 0 && (
        <div className="flex flex-col">
          {notifications.map(n => (
            <div
              key={n.id}
              onClick={() => !n.read && markRead(n.id)}
              className={`flex items-start gap-3 px-4 py-3.5 border-b border-gray-800 cursor-pointer transition-colors ${
                !n.read ? 'bg-gray-800/40 hover:bg-gray-800/60' : 'hover:bg-gray-800/20'
              }`}
            >
              <span className="text-xl mt-0.5 flex-shrink-0">{SEV_ICONS[n.severity] || '●'}</span>
              <div className="flex-1 min-w-0">
                <div className={`text-sm ${n.read ? 'text-gray-300' : 'text-white font-medium'}`}>{n.title}</div>
                <div className="text-xs text-gray-400 mt-0.5 leading-relaxed">{n.message}</div>
                {n.scan_id && (
                  <div className="text-xs text-gray-600 mt-1 font-mono">{n.scan_id}</div>
                )}
              </div>
              <div className="flex-shrink-0 flex items-center gap-2">
                <span className="text-xs text-gray-500 whitespace-nowrap">{fmtTs(n.created_at)}</span>
                {!n.read && <div className="w-2 h-2 bg-cyan-400 rounded-full" />}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
