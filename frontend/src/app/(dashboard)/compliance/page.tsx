'use client';

import { useEffect, useState } from 'react';
import { complianceApi, scansListApi } from '@/lib/api';

const OWASP_COLORS: Record<string, string> = {
  'A01:2021': 'text-red-400', 'A02:2021': 'text-orange-400', 'A03:2021': 'text-red-400',
  'A04:2021': 'text-yellow-400', 'A05:2021': 'text-orange-400', 'A06:2021': 'text-orange-400',
  'A07:2021': 'text-red-400', 'A08:2021': 'text-yellow-400', 'A09:2021': 'text-gray-400',
  'A10:2021': 'text-orange-400',
};

export default function CompliancePage() {
  const [scans, setScans] = useState<any[]>([]);
  const [selectedScan, setSelectedScan] = useState('');
  const [compliance, setCompliance] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    scansListApi.list().then(data => {
      setScans(data);
      if (data.length > 0) {
        const id = data[0].scan_id || data[0].id;
        setSelectedScan(id);
        loadCompliance(id);
      }
    }).catch(() => {});
  }, []);

  async function loadCompliance(id: string) {
    if (!id) return;
    setLoading(true); setError('');
    try { setCompliance(await complianceApi.score(id)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Compliance & Mapping</h1>
          <p className="text-gray-400 text-sm mt-1">OWASP Top 10 · CWE · MITRE ATT&amp;CK · NIS2 · ISO 27001</p>
        </div>
        <select value={selectedScan} onChange={e => { setSelectedScan(e.target.value); loadCompliance(e.target.value); }}
          className="bg-gray-800 border border-gray-700 text-white px-3 py-1.5 text-sm max-w-xs">
          {scans.map(s => (
            <option key={s.scan_id || s.id} value={s.scan_id || s.id}>
              {s.target} ({(s.scan_id || s.id)?.slice(0, 8)})
            </option>
          ))}
        </select>
      </div>

      {error && <div className="text-red-400 border border-red-400 p-3 mb-4 text-sm">{error}</div>}
      {loading && <div className="text-gray-400 text-center py-8">Laden…</div>}

      {compliance && !loading && (
        <>
          {/* Summary */}
          <div className="flex gap-4 mb-8">
            <div className="bg-gray-800/50 border border-gray-700 p-4">
              <div className="text-xs text-gray-500 uppercase mb-1">OWASP Categorieën gevonden</div>
              <div className={`text-3xl font-bold font-mono ${compliance.owasp_categories_found > 3 ? 'text-red-400' : 'text-green-400'}`}>
                {compliance.owasp_categories_found} / 10
              </div>
            </div>
            <div className="bg-gray-800/50 border border-gray-700 p-4">
              <div className="text-xs text-gray-500 uppercase mb-1">Dekking</div>
              <div className="text-3xl font-bold font-mono text-white">{compliance.coverage_pct}%</div>
            </div>
          </div>

          {/* OWASP Top 10 Grid */}
          <section className="mb-8">
            <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400 mb-4 border-b border-gray-700 pb-2">
              OWASP Top 10 (2021)
            </h2>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {(compliance.owasp_top10 || []).map((cat: any) => {
                const hits = compliance.owasp_findings?.[cat.id] || [];
                return (
                  <div key={cat.id} className={`border p-3 ${hits.length > 0 ? 'border-red-500/50 bg-red-500/5' : 'border-gray-700/50 opacity-60'}`}>
                    <div className={`text-xs font-mono font-bold mb-1 ${OWASP_COLORS[cat.id] || 'text-gray-400'}`}>{cat.id}</div>
                    <div className="text-xs font-medium leading-snug mb-2">{cat.name}</div>
                    {hits.length > 0 ? (
                      <div className="flex flex-col gap-1">
                        {hits.map((h: any, i: number) => (
                          <div key={i} className="flex flex-wrap gap-1">
                            <span className="text-orange-400 border border-orange-400/50 text-xs px-1 font-mono">{h.cwe}</span>
                            {h.mitre && <span className="text-blue-400 border border-blue-400/50 text-xs px-1 font-mono">T{h.mitre}</span>}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-xs text-green-400">✓ Niet aangetroffen</div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Regulatory notes */}
          <section>
            <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400 mb-4 border-b border-gray-700 pb-2">
              Regelgeving
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {[
                { title: 'NIS2', text: compliance.nis2_note },
                { title: 'ISO 27001', text: compliance.iso27001_note },
                { title: 'GDPR', text: 'Artikel 32: Passende technische maatregelen zijn verplicht. Kwetsbaarheden kunnen meldingsplicht activeren.' },
              ].map(r => (
                <div key={r.title} className="bg-gray-800/30 border border-gray-700 p-4">
                  <h3 className="text-cyan-400 font-bold text-sm mb-2">{r.title}</h3>
                  <p className="text-gray-400 text-xs leading-relaxed">{r.text}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {!loading && !compliance && scans.length === 0 && (
        <div className="text-gray-400 text-center py-12">Start eerst een scan om compliance data te zien.</div>
      )}
    </div>
  );
}
