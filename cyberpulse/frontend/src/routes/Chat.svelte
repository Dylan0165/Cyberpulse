<script lang="ts">
  import { onMount } from 'svelte';
  import { chatWithScan, getChatHistory, getRecentScans } from '../lib/api';

  export let scanId: string = '';

  let scans: any[] = [];
  let selectedScan = scanId;
  let messages: { role: 'user' | 'assistant'; content: string; ts?: string }[] = [];
  let input = '';
  let loading = false;
  let historyLoading = true;
  let chatContainer: HTMLElement;

  const SUGGESTED = [
    'Wat zijn de kritieke bevindingen?',
    'Hoe hoog is het risico voor mijn organisatie?',
    'Wat moet ik als eerste oplossen?',
    'Zijn er tekenen van actieve aanvallen?',
    'Leg de SQL injection bevinding uit.',
    'Geef me een herstelplan voor de high-severity problemen.',
  ];

  onMount(async () => {
    scans = await getRecentScans(30);
    if (!selectedScan && scans.length > 0) selectedScan = scans[0].scan_id;
    if (selectedScan) await loadHistory();
    historyLoading = false;
  });

  async function loadHistory() {
    if (!selectedScan) return;
    try {
      messages = await getChatHistory(selectedScan);
    } catch {
      messages = [];
    }
    scrollBottom();
  }

  async function send(text?: string) {
    const msg = (text || input).trim();
    if (!msg || !selectedScan || loading) return;
    input = '';
    messages = [...messages, { role: 'user', content: msg, ts: new Date().toISOString() }];
    loading = true;
    scrollBottom();
    try {
      const { answer } = await chatWithScan(selectedScan, msg, messages.slice(-10));
      messages = [...messages, { role: 'assistant', content: answer, ts: new Date().toISOString() }];
    } catch (e: any) {
      messages = [...messages, { role: 'assistant', content: `Fout: ${e.message}`, ts: new Date().toISOString() }];
    } finally {
      loading = false;
      scrollBottom();
    }
  }

  function scrollBottom() {
    setTimeout(() => {
      if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 50);
  }

  async function changeScan() {
    messages = [];
    historyLoading = true;
    await loadHistory();
    historyLoading = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function formatTs(ts: string): string {
    try { return new Date(ts).toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' }); } catch { return ''; }
  }
</script>

<div class="chat-page">
  <header class="page-header">
    <h1>AI Pentest Assistent</h1>
    <div class="scan-select-wrap">
      <label for="scan-select">Scan:</label>
      <select id="scan-select" bind:value={selectedScan} on:change={changeScan}>
        {#each scans as s}
          <option value={s.scan_id}>{s.target} – {s.scan_type} ({s.scan_id?.slice(0, 8)})</option>
        {/each}
      </select>
    </div>
  </header>

  {#if !selectedScan}
    <div class="empty-state">Geen scan geselecteerd. Start eerst een scan.</div>
  {:else}
    <div class="chat-layout">
      <!-- Suggestions on the left -->
      <aside class="suggestions">
        <h3>Suggesties</h3>
        {#each SUGGESTED as s}
          <button class="suggestion-btn" on:click={() => send(s)}>{s}</button>
        {/each}
      </aside>

      <!-- Chat on the right -->
      <div class="chat-area">
        <div class="messages" bind:this={chatContainer}>
          {#if historyLoading}
            <div class="loading">Laden…</div>
          {:else if messages.length === 0}
            <div class="intro">
              <p>Stel een vraag over scan <strong>{selectedScan?.slice(0, 8)}</strong>.</p>
            </div>
          {:else}
            {#each messages as msg}
              <div class="message {msg.role}">
                <div class="bubble">
                  {msg.content}
                  {#if msg.ts}
                    <span class="ts">{formatTs(msg.ts)}</span>
                  {/if}
                </div>
              </div>
            {/each}
            {#if loading}
              <div class="message assistant">
                <div class="bubble thinking">
                  <span>●</span><span>●</span><span>●</span>
                </div>
              </div>
            {/if}
          {/if}
        </div>

        <div class="input-area">
          <textarea
            bind:value={input}
            on:keydown={handleKeydown}
            placeholder="Stuur een bericht… (Enter om te verzenden)"
            rows="2"
            disabled={loading}
          ></textarea>
          <button class="send-btn" on:click={() => send()} disabled={!input.trim() || loading}>
            {loading ? '…' : '→'}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .chat-page { padding: 2rem; height: calc(100vh - 4rem); display: flex; flex-direction: column; }
  .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .scan-select-wrap { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: var(--text-muted, #888); }
  .scan-select-wrap select {
    background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.3rem 0.75rem; font-size: 0.875rem; max-width: 360px;
  }
  .chat-layout { display: flex; gap: 1.5rem; flex: 1; overflow: hidden; }
  .suggestions { width: 220px; flex-shrink: 0; display: flex; flex-direction: column; gap: 0.5rem; }
  .suggestions h3 { font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted, #888); margin: 0 0 0.5rem; }
  .suggestion-btn {
    text-align: left; background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #ccc); padding: 0.5rem 0.75rem; font-size: 0.8rem; cursor: pointer; line-height: 1.4;
  }
  .suggestion-btn:hover { border-color: var(--highlight, #0ff); color: var(--text, #fff); }
  .chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem;
              padding: 0.5rem; background: var(--bg, #0a0a0a); border: 1px solid var(--border, #222); }
  .message { display: flex; }
  .message.user { justify-content: flex-end; }
  .message.assistant { justify-content: flex-start; }
  .bubble {
    max-width: 72%; padding: 0.6rem 1rem; font-size: 0.875rem; line-height: 1.6;
    white-space: pre-wrap; word-break: break-word; position: relative;
  }
  .message.user .bubble { background: var(--accent, #1a3a3a); border: 1px solid #0ff4; }
  .message.assistant .bubble { background: var(--surface, #1a1a1a); border: 1px solid var(--border, #333); }
  .ts { display: block; font-size: 0.7rem; color: var(--text-muted, #666); margin-top: 0.25rem; text-align: right; }
  .thinking span { animation: pulse 1s infinite; display: inline-block; margin-right: 2px; }
  .thinking span:nth-child(2) { animation-delay: 0.2s; }
  .thinking span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes pulse { 0%, 100% { opacity: 0.2; } 50% { opacity: 1; } }
  .input-area { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
  .input-area textarea {
    flex: 1; background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.5rem 0.75rem; font-size: 0.875rem; resize: none; outline: none;
    font-family: inherit;
  }
  .input-area textarea:focus { border-color: var(--highlight, #0ff); }
  .send-btn {
    background: var(--accent, #1a1a1a); border: 1px solid var(--highlight, #0ff);
    color: var(--highlight, #0ff); padding: 0.5rem 1.25rem; cursor: pointer; font-size: 1.1rem;
  }
  .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .loading, .empty-state, .intro { color: var(--text-muted, #888); text-align: center; padding: 2rem; font-size: 0.9rem; }
</style>
