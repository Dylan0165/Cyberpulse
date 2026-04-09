'use client';

import { useEffect, useState } from 'react';
import { webhooksApi, apiKeysApi } from '@/lib/api';

const EVENTS = ['scan_completed', 'scan_failed', 'critical_finding', 'high_finding', 'scan_started'];

type Tab = 'webhooks' | 'apikeys';

export default function IntegrationsPage() {
  const [tab, setTab] = useState<Tab>('webhooks');
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [newKeyVal, setNewKeyVal] = useState('');

  const [wUrl, setWUrl] = useState('');
  const [wEvents, setWEvents] = useState<string[]>(['scan_completed']);
  const [wLoading, setWLoading] = useState(false);

  const [kName, setKName] = useState('');
  const [kScope, setKScope] = useState('read');
  const [kLoading, setKLoading] = useState(false);

  async function loadWebhooks() { setWebhooks(await webhooksApi.list()); }
  async function loadKeys() { setApiKeys(await apiKeysApi.list()); }

  useEffect(() => {
    Promise.all([loadWebhooks(), loadKeys()]).catch(e => setError(e.message));
  }, []);

  async function addWebhook(e: React.FormEvent) {
    e.preventDefault();
    if (!wUrl.trim()) return;
    setWLoading(true);
    try {
      await webhooksApi.create({ url: wUrl.trim(), events: wEvents });
      setWUrl('');
      await loadWebhooks();
    } catch (err: any) { setError(err.message); }
    finally { setWLoading(false); }
  }

  async function addKey(e: React.FormEvent) {
    e.preventDefault();
    if (!kName.trim()) return;
    setKLoading(true);
    try {
      const result = await apiKeysApi.create({ name: kName.trim(), scope: kScope });
      setNewKeyVal(result.key);
      setKName('');
      await loadKeys();
    } catch (err: any) { setError(err.message); }
    finally { setKLoading(false); }
  }

  function toggleEvent(ev: string) {
    setWEvents(prev => prev.includes(ev) ? prev.filter(x => x !== ev) : [...prev, ev]);
  }

  const inp = "bg-gray-900 border border-gray-700 text-white px-3 py-2 text-sm focus:border-cyan-400 focus:outline-none";

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Integraties & API</h1>
        <p className="text-gray-400 text-sm mt-1">Webhooks, API keys en externe koppelingen</p>
      </div>

      <div className="flex border-b border-gray-700 mb-6">
        {(['webhooks', 'apikeys'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-5 py-2.5 text-sm border-b-2 -mb-px transition-colors ${tab === t ? 'border-cyan-400 text-white' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
            {t === 'webhooks' ? 'Webhooks' : 'API Keys'}
          </button>
        ))}
      </div>

      {error && (
        <div className="text-red-400 border border-red-400 p-3 mb-4 text-sm flex justify-between">
          {error} <button onClick={() => setError('')} className="ml-2">✕</button>
        </div>
      )}

      {tab === 'webhooks' ? (
        <section>
          <form onSubmit={addWebhook} className="flex flex-col gap-3 mb-6">
            <input className={`${inp} w-full`} value={wUrl} onChange={e => setWUrl(e.target.value)} placeholder="https://hooks.example.com/..." />
            <div className="flex flex-wrap gap-3">
              {EVENTS.map(ev => (
                <label key={ev} className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
                  <input type="checkbox" checked={wEvents.includes(ev)} onChange={() => toggleEvent(ev)} className="accent-cyan-400" />
                  {ev}
                </label>
              ))}
            </div>
            <button type="submit" disabled={wLoading || !wUrl.trim()}
              className="self-start bg-gray-700 border border-gray-600 text-white px-5 py-2 text-sm hover:border-cyan-400 disabled:opacity-50">
              {wLoading ? 'Aanmaken…' : '+ Webhook toevoegen'}
            </button>
          </form>

          <div className="flex flex-col gap-2">
            {webhooks.length === 0
              ? <div className="text-gray-500 text-sm py-6 text-center">Geen webhooks geconfigureerd.</div>
              : webhooks.map(wh => (
                <div key={wh.id} className="flex items-center gap-3 p-3 bg-gray-800/30 border border-gray-700 flex-wrap">
                  <span className="font-mono text-xs text-cyan-400 flex-1">{wh.url}</span>
                  <div className="flex gap-1 flex-wrap">
                    {(wh.events || []).map((ev: string) => (
                      <span key={ev} className="bg-gray-700 text-xs px-1.5 py-0.5">{ev}</span>
                    ))}
                  </div>
                  <span className={`text-xs ${wh.enabled ? 'text-green-400' : 'text-gray-500'}`}>{wh.enabled ? 'Actief' : 'Inactief'}</span>
                  <button onClick={() => webhooksApi.remove(wh.id).then(loadWebhooks)} className="text-gray-600 hover:text-red-400 text-sm">✕</button>
                </div>
              ))}
          </div>
        </section>
      ) : (
        <section>
          <form onSubmit={addKey} className="flex flex-wrap gap-3 items-end mb-6">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">Naam</span>
              <input className={`${inp} w-52`} value={kName} onChange={e => setKName(e.target.value)} placeholder="bijv. CI/CD pipeline" />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">Scope</span>
              <select className={inp} value={kScope} onChange={e => setKScope(e.target.value)}>
                <option value="read">Read-only</option>
                <option value="scan">Scan</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button type="submit" disabled={kLoading || !kName.trim()}
              className="bg-gray-700 border border-gray-600 text-white px-5 py-2 text-sm hover:border-cyan-400 disabled:opacity-50">
              {kLoading ? 'Aanmaken…' : '+ Aanmaken'}
            </button>
          </form>

          {newKeyVal && (
            <div className="bg-green-900/20 border border-green-500/50 p-3 mb-4 flex items-center gap-3 flex-wrap">
              <span className="text-xs text-gray-400">Nieuwe key (eenmalig zichtbaar):</span>
              <code className="text-green-400 font-mono text-xs flex-1 break-all">{newKeyVal}</code>
              <button onClick={() => navigator.clipboard.writeText(newKeyVal)}
                className="text-xs border border-green-500 text-green-400 px-2 py-0.5">Kopieer</button>
              <button onClick={() => setNewKeyVal('')} className="text-gray-500 text-sm">✕</button>
            </div>
          )}

          <div className="flex flex-col gap-2">
            {apiKeys.length === 0
              ? <div className="text-gray-500 text-sm py-6 text-center">Geen API keys aangemaakt.</div>
              : apiKeys.map(k => (
                <div key={k.id} className="flex items-center gap-3 p-3 bg-gray-800/30 border border-gray-700 flex-wrap">
                  <span className="font-semibold text-sm min-w-24">{k.name}</span>
                  <code className="font-mono text-xs text-gray-500">{k.key}</code>
                  <span className="bg-blue-900/30 border border-blue-700/50 text-blue-400 text-xs px-2 py-0.5">{k.scope}</span>
                  <span className="text-xs text-gray-600 flex-1">{k.last_used ? `Gebruikt: ${new Date(k.last_used).toLocaleDateString('nl-NL')}` : 'Nog niet gebruikt'}</span>
                  <button onClick={() => apiKeysApi.remove(k.id).then(loadKeys)} className="text-gray-600 hover:text-red-400 text-sm">✕</button>
                </div>
              ))}
          </div>
        </section>
      )}
    </div>
  );
}
