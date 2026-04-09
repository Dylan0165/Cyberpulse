'use client';

import { useEffect, useRef, useState } from 'react';
import { chatApi, scansListApi } from '@/lib/api';

interface Message { role: 'user' | 'assistant'; content: string; ts: string; }

const SUGGESTED = [
  'Wat zijn de kritieke bevindingen?',
  'Hoe hoog is het risico?',
  'Wat must ik als eerste oplossen?',
  'Zijn er tekenen van actieve aanvallen?',
  'Geef een herstelplan voor high-severity problemen.',
];

export default function ChatPage() {
  const [scans, setScans] = useState<any[]>([]);
  const [selectedScan, setSelectedScan] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scansListApi.list().then(data => {
      setScans(data);
      if (data.length > 0) setSelectedScan(data[0].scan_id || data[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedScan) return;
    chatApi.history(selectedScan).then(h => setMessages(h || [])).catch(() => setMessages([]));
  }, [selectedScan]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function send(text?: string) {
    const msg = (text || input).trim();
    if (!msg || !selectedScan || loading) return;
    setInput('');
    const ts = new Date().toISOString();
    setMessages(prev => [...prev, { role: 'user', content: msg, ts }]);
    setLoading(true);
    try {
      const { answer } = await chatApi.send(selectedScan, msg, messages.slice(-10));
      setMessages(prev => [...prev, { role: 'assistant', content: answer, ts: new Date().toISOString() }]);
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Fout: ${e.message}`, ts: new Date().toISOString() }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] p-6 max-w-5xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">AI Pentest Assistent</h1>
        <select
          value={selectedScan}
          onChange={e => setSelectedScan(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white px-3 py-1.5 text-sm max-w-xs"
        >
          {scans.map(s => (
            <option key={s.scan_id || s.id} value={s.scan_id || s.id}>
              {s.target} – {s.scan_type} ({(s.scan_id || s.id)?.slice(0, 8)})
            </option>
          ))}
        </select>
      </div>

      <div className="flex gap-4 flex-1 overflow-hidden">
        {/* Suggestions sidebar */}
        <aside className="w-48 flex-shrink-0 flex flex-col gap-2">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Suggesties</p>
          {SUGGESTED.map(s => (
            <button key={s} onClick={() => send(s)}
              className="text-left text-xs text-gray-400 border border-gray-700 p-2.5 hover:border-cyan-400 hover:text-white leading-relaxed">
              {s}
            </button>
          ))}
        </aside>

        {/* Chat area */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto flex flex-col gap-3 p-3 bg-gray-900 border border-gray-800">
            {messages.length === 0 && !loading && (
              <div className="text-gray-500 text-sm text-center py-8">
                Stel een vraag over de geselecteerde scan.
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] px-4 py-2.5 text-sm whitespace-pre-wrap ${
                  m.role === 'user'
                    ? 'bg-gray-700 border border-gray-600'
                    : 'bg-gray-800 border border-gray-700'
                }`}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-800 border border-gray-700 px-4 py-2.5 text-sm text-gray-400">
                  Denken…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="flex gap-2 mt-2">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Stuur een bericht… (Enter om te verzenden)"
              rows={2}
              disabled={loading}
              className="flex-1 bg-gray-800 border border-gray-700 text-white px-3 py-2 text-sm resize-none focus:border-cyan-400 focus:outline-none"
            />
            <button onClick={() => send()} disabled={!input.trim() || loading}
              className="bg-gray-700 border border-cyan-400 text-cyan-400 px-5 text-lg disabled:opacity-40">
              →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
