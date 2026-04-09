'use client';

import { useEffect, useState } from 'react';
import { schedulesApi } from '@/lib/api';

interface Schedule {
  id: string;
  target: string;
  interval: string;
  scan_type: string;
  scan_mode: string;
  enabled: boolean;
  next_run: string | null;
  last_run: string | null;
}

export default function SchedulePage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    target: '', scan_type: 'quick', scan_mode: 'blackbox',
    target_type: 'web', interval: 'weekly', enabled: true,
  });

  async function load() {
    setLoading(true);
    try { setSchedules(await schedulesApi.list()); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.target.trim()) return;
    setSubmitting(true);
    try {
      await schedulesApi.create(form);
      setShowForm(false);
      setForm({ target: '', scan_type: 'quick', scan_mode: 'blackbox', target_type: 'web', interval: 'weekly', enabled: true });
      await load();
    } catch (err: any) { setError(err.message); }
    finally { setSubmitting(false); }
  }

  async function remove(id: string) { await schedulesApi.remove(id); await load(); }
  async function toggle(id: string, enabled: boolean) { await schedulesApi.toggle(id, !enabled); await load(); }

  function fmtDate(ts: string | null) {
    if (!ts) return '—';
    try { return new Date(ts).toLocaleString('nl-NL', { dateStyle: 'short', timeStyle: 'short' }); } catch { return ts; }
  }

  const inp = "bg-gray-800 border border-gray-700 text-white px-3 py-2 text-sm focus:border-cyan-400 focus:outline-none";

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Geplande Scans</h1>
          <p className="text-gray-400 text-sm mt-1">{schedules.length} gepland</p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          className="bg-gray-800 border border-gray-700 text-white px-4 py-2 text-sm hover:border-cyan-400"
        >
          {showForm ? '✕ Annuleer' : '+ Nieuwe planning'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} className="bg-gray-800/50 border border-gray-700 p-5 mb-6">
          <h2 className="text-sm font-semibold mb-4">Nieuwe scan plannen</h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <label className="flex flex-col gap-1 text-xs text-gray-400">
              Target *
              <input className={inp} value={form.target} onChange={e => setForm({ ...form, target: e.target.value })} placeholder="example.com" required />
            </label>
            <label className="flex flex-col gap-1 text-xs text-gray-400">
              Interval
              <select className={inp} value={form.interval} onChange={e => setForm({ ...form, interval: e.target.value })}>
                <option value="daily">Dagelijks</option>
                <option value="weekly">Wekelijks</option>
                <option value="monthly">Maandelijks</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-gray-400">
              Scan type
              <select className={inp} value={form.scan_type} onChange={e => setForm({ ...form, scan_type: e.target.value })}>
                <option value="quick">Quick</option>
                <option value="full">Full</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-gray-400">
              Modus
              <select className={inp} value={form.scan_mode} onChange={e => setForm({ ...form, scan_mode: e.target.value })}>
                <option value="blackbox">Blackbox</option>
                <option value="greybox">Greybox</option>
                <option value="whitebox">Whitebox</option>
              </select>
            </label>
          </div>
          <button type="submit" disabled={submitting || !form.target.trim()}
            className="mt-4 bg-gray-700 border border-gray-600 text-white px-5 py-2 text-sm hover:border-cyan-400 disabled:opacity-50">
            {submitting ? 'Plannen…' : 'Planning aanmaken'}
          </button>
        </form>
      )}

      {error && <div className="text-red-400 border border-red-400 p-3 mb-4 text-sm">{error}</div>}
      {loading && <div className="text-gray-400 text-center py-8">Laden…</div>}

      {!loading && schedules.length === 0 && (
        <div className="text-gray-400 text-center py-12">Geen geplande scans aangemaakt.</div>
      )}

      {!loading && schedules.length > 0 && (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
              {['Target', 'Interval', 'Type / Modus', 'Volgende scan', 'Status', ''].map(h => (
                <th key={h} className="px-4 py-3 bg-gray-800/50 border-b border-gray-700">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {schedules.map(s => (
              <tr key={s.id} className={`border-b border-gray-800 ${!s.enabled ? 'opacity-50' : ''}`}>
                <td className="px-4 py-3 font-mono text-xs text-cyan-400">{s.target}</td>
                <td className="px-4 py-3">
                  <span className="bg-gray-700 text-xs px-2 py-0.5">{s.interval}</span>
                </td>
                <td className="px-4 py-3 text-gray-400">{s.scan_type} / {s.scan_mode}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(s.next_run)}</td>
                <td className="px-4 py-3">
                  <button onClick={() => toggle(s.id, s.enabled)}
                    className={`text-xs px-2 py-0.5 border ${s.enabled ? 'border-green-500 text-green-400' : 'border-gray-600 text-gray-500'}`}>
                    {s.enabled ? 'Actief' : 'Inactief'}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button onClick={() => remove(s.id)} className="text-gray-600 hover:text-red-400 text-sm">✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
