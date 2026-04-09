'use client';

import { useEffect, useState } from 'react';
import { auditApi } from '@/lib/api';

const ACTION_ICONS: Record<string, string> = {
  scan_started: '▶', scan_completed: '✓', scan_failed: '✗', scan_stopped: '■',
  scan_paused: '⏸', scan_resumed: '⏵', scan_authorized: '🔒', finding_marked: '🏷',
  schedule_created: '📅', webhook_created: '🔗', api_key_created: '🔑',
  deduplication: '♻', settings_saved: '⚙',
};

export default function AuditPage() {
  const [log, setLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    auditApi.list(200)
      .then(setLog)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function fmtTs(ts: string) {
    try { return new Date(ts).toLocaleString('nl-NL', { dateStyle: 'short', timeStyle: 'medium' }); } catch { return ts; }
  }

  const filtered = log.filter(e =>
    !search ||
    e.action?.toLowerCase().includes(search.toLowerCase()) ||
    e.detail?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Audit Log</h1>
          <p className="text-gray-400 text-sm mt-1">Onveranderlijk overzicht van alle systeemacties</p>
        </div>
        <button onClick={() => { setLoading(true); auditApi.list(200).then(setLog).finally(() => setLoading(false)); }}
          className="bg-gray-800 border border-gray-700 text-gray-400 px-4 py-2 text-sm hover:border-cyan-400 hover:text-white">
          ↻ Vernieuwen
        </button>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <input
          type="text"
          placeholder="Zoek op actie of detail…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white px-4 py-2 w-72 text-sm focus:border-cyan-400 focus:outline-none"
        />
        <span className="text-xs text-gray-500">{filtered.length} van {log.length} entries</span>
      </div>

      {loading && <div className="text-gray-400 text-center py-8">Laden…</div>}

      {!loading && filtered.length === 0 && (
        <div className="text-gray-400 text-center py-12">Geen audit entries.</div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="overflow-hidden border border-gray-800">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wider bg-gray-800/50">
                <th className="px-4 py-2.5 border-b border-gray-700">Actie</th>
                <th className="px-4 py-2.5 border-b border-gray-700">Detail</th>
                <th className="px-4 py-2.5 border-b border-gray-700">Tijdstip</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry, i) => (
                <tr key={i} className={`border-b border-gray-800/50 ${i % 2 === 0 ? 'bg-gray-900/30' : ''}`}>
                  <td className="px-4 py-2.5">
                    <span className="mr-2 text-base">{ACTION_ICONS[entry.action] ?? '•'}</span>
                    <span className="capitalize">{entry.action?.replace(/_/g, ' ')}</span>
                  </td>
                  <td className="px-4 py-2.5 text-gray-400 max-w-xs overflow-hidden text-ellipsis whitespace-nowrap">
                    {entry.detail || '—'}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{fmtTs(entry.ts)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
