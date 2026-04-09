'use client';

import { useEffect, useState } from 'react';
import { assetsApi } from '@/lib/api';

interface Asset {
  target: string;
  target_type: string;
  last_scan: string;
  last_scan_id: string;
  scan_count: number;
  risk_score: number | null;
  total_findings: number;
  open_ports: number[];
  os_guess: string;
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sortCol, setSortCol] = useState<keyof Asset>('risk_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    assetsApi.list()
      .then(setAssets)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function toggleSort(col: keyof Asset) {
    if (sortCol === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc');
    else { setSortCol(col); setSortDir('desc'); }
  }

  const filtered = assets
    .filter(a =>
      a.target.toLowerCase().includes(search.toLowerCase()) ||
      (a.os_guess || '').toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      const va = (a[sortCol] ?? 0) as number;
      const vb = (b[sortCol] ?? 0) as number;
      return sortDir === 'desc' ? (va < vb ? 1 : -1) : (va > vb ? 1 : -1);
    });

  function riskClass(score: number | null) {
    if (score === null) return 'text-gray-500';
    if (score >= 80) return 'text-red-400';
    if (score >= 60) return 'text-orange-400';
    if (score >= 40) return 'text-yellow-400';
    return 'text-green-400';
  }

  function fmtDate(ts: string) {
    try { return new Date(ts).toLocaleDateString('nl-NL'); } catch { return ts; }
  }

  const SortIcon = ({ col }: { col: string }) =>
    sortCol === col ? (sortDir === 'desc' ? ' ↓' : ' ↑') : '';

  return (
    <div className="p-6 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Asset Inventaris</h1>
        <p className="text-gray-400 text-sm mt-1">{assets.length} ontdekte assets</p>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Zoek op target of OS..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white px-4 py-2 w-72 text-sm outline-none focus:border-cyan-400"
        />
      </div>

      {loading && <div className="text-gray-400 py-8 text-center">Laden…</div>}
      {error && <div className="text-red-400 border border-red-400 p-3 mb-4 text-sm">{error}</div>}

      {!loading && !error && filtered.length === 0 && (
        <div className="text-gray-400 py-12 text-center">
          Geen assets gevonden. Start eerst een scan.
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                {(['target', 'open_ports', 'os_guess', 'scan_count', 'total_findings', 'risk_score', 'last_scan'] as const).map(col => (
                  <th
                    key={col}
                    onClick={() => toggleSort(col as keyof Asset)}
                    className="px-4 py-3 bg-gray-800/50 border-b border-gray-700 cursor-pointer hover:text-white"
                  >
                    {col.replace(/_/g, ' ')}
                    {sortCol === col ? (sortDir === 'desc' ? ' ↓' : ' ↑') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(a => (
                <tr key={a.target} className="border-b border-gray-800 hover:bg-gray-800/30">
                  <td className="px-4 py-3 font-mono text-xs text-cyan-400">{a.target}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(a.open_ports || []).slice(0, 6).map(p => (
                        <span key={p} className="bg-gray-700 text-xs px-1.5 py-0.5 font-mono">{p}</span>
                      ))}
                      {(a.open_ports?.length || 0) > 6 && (
                        <span className="text-gray-500 text-xs">+{a.open_ports.length - 6}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{a.os_guess || '—'}</td>
                  <td className="px-4 py-3 text-center">{a.scan_count}</td>
                  <td className="px-4 py-3 text-center">{a.total_findings || 0}</td>
                  <td className="px-4 py-3">
                    <span className={`font-mono font-bold ${riskClass(a.risk_score)}`}>
                      {a.risk_score !== null ? `${a.risk_score}/100` : '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(a.last_scan)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
