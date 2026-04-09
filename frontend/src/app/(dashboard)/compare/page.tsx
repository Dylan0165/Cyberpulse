'use client';

import { useEffect, useState } from 'react';
import { compareApi, scansListApi } from '@/lib/api';

type TabType = 'new' | 'resolved' | 'unchanged';

function SevBadge({ sev }: { sev: string }) {
  const cls: Record<string, string> = {
    critical: 'text-red-400 border-red-400',
    high: 'text-orange-400 border-orange-400',
    medium: 'text-yellow-400 border-yellow-400',
    low: 'text-green-400 border-green-400',
    info: 'text-gray-400 border-gray-600',
  };
  return (
    <span className={`border text-xs px-1.5 py-0.5 font-mono font-bold uppercase ${cls[sev?.toLowerCase()] ?? cls.info}`}>
      {sev}
    </span>
  );
}

export default function ComparePage() {
  const [scans, setScans] = useState<any[]>([]);
  const [scanA, setScanA] = useState('');
  const [scanB, setScanB] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<TabType>('new');

  useEffect(() => {
    scansListApi.list().then(data => {
      setScans(data);
      if (data.length >= 2) {
        setScanA(data[1].scan_id || data[1].id);
        setScanB(data[0].scan_id || data[0].id);
      } else if (data.length === 1) {
        setScanA(data[0].scan_id || data[0].id);
      }
    }).catch(() => {});
  }, []);

  async function compare() {
    if (!scanA || !scanB || scanA === scanB) return;
    setLoading(true); setError(''); setResult(null);
    try { setResult(await compareApi.compare(scanA, scanB)); setTab('new'); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  const tabData = result ? { new: result.new, resolved: result.resolved, unchanged: result.unchanged } : { new: [], resolved: [], unchanged: [] };
  const tabCounts = result?.summary ?? { new_count: 0, resolved_count: 0, unchanged_count: 0 };

  const selectCls = "bg-gray-800 border border-gray-700 text-white px-3 py-2 text-sm";

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Scan Vergelijken</h1>
        <p className="text-gray-400 text-sm mt-1">Delta analyse — nieuwe, opgeloste en ongewijzigde bevindingen</p>
      </div>

      <div className="flex items-end gap-3 mb-6 flex-wrap">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-gray-500 uppercase">Baseline (oud)</span>
          <select className={selectCls} value={scanA} onChange={e => setScanA(e.target.value)}>
            {scans.map(s => <option key={s.scan_id || s.id} value={s.scan_id || s.id}>{s.target} ({(s.scan_id || s.id)?.slice(0, 8)})</option>)}
          </select>
        </div>
        <span className="text-2xl text-gray-600 mb-0.5">→</span>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-gray-500 uppercase">Nieuwe scan</span>
          <select className={selectCls} value={scanB} onChange={e => setScanB(e.target.value)}>
            {scans.map(s => <option key={s.scan_id || s.id} value={s.scan_id || s.id}>{s.target} ({(s.scan_id || s.id)?.slice(0, 8)})</option>)}
          </select>
        </div>
        <button onClick={compare} disabled={!scanA || !scanB || scanA === scanB || loading}
          className="bg-gray-700 border border-gray-600 text-white px-5 py-2 text-sm hover:border-cyan-400 disabled:opacity-50 mb-0">
          {loading ? 'Vergelijken…' : 'Vergelijk'}
        </button>
      </div>

      {error && <div className="text-red-400 border border-red-400 p-3 mb-4 text-sm">{error}</div>}

      {result && (
        <>
          <div className="flex gap-4 mb-6">
            {([['new', tabCounts.new_count, 'text-red-400'], ['resolved', tabCounts.resolved_count, 'text-green-400'], ['unchanged', tabCounts.unchanged_count, 'text-gray-400']] as const).map(([t, count, cls]) => (
              <button key={t} onClick={() => setTab(t as TabType)}
                className={`flex-1 p-4 border text-center transition-colors ${tab === t ? `border-current ${cls}` : 'border-gray-700 text-gray-500 hover:border-gray-500'}`}>
                <div className={`text-3xl font-bold font-mono ${cls}`}>{count}</div>
                <div className="text-xs uppercase mt-1">{t === 'new' ? 'Nieuw' : t === 'resolved' ? 'Opgelost' : 'Ongewijzigd'}</div>
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-2">
            {tabData[tab].length === 0 ? (
              <div className="text-gray-400 text-center py-8">
                {tab === 'new' ? '✓ Geen nieuwe bevindingen' : tab === 'resolved' ? 'Geen opgeloste bevindingen' : 'Geen ongewijzigde bevindingen'}
              </div>
            ) : (
              tabData[tab].map((f: any, i: number) => (
                <div key={i} className={`flex items-center gap-3 p-3 border border-gray-800 bg-gray-800/30 flex-wrap ${tab === 'resolved' ? 'opacity-60' : ''}`}>
                  <SevBadge sev={f.severity || 'info'} />
                  <span className="font-mono text-xs text-cyan-400">{f.type || 'bevinding'}</span>
                  <span className="text-sm flex-1">{f.title || f.beschrijving || '—'}</span>
                  {tab === 'resolved' && <span className="text-xs text-green-400">✓ Opgelost</span>}
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
