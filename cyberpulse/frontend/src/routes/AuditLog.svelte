<script lang="ts">
  import { onMount } from 'svelte';
  import { getAuditLog } from '../lib/api';

  let log: any[] = [];
  let loading = true;
  let error = '';
  let search = '';
  let limit = 100;

  onMount(() => reload());

  async function reload() {
    loading = true;
    try {
      log = await getAuditLog(limit);
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  $: filtered = log.filter(e =>
    !search ||
    e.action?.toLowerCase().includes(search.toLowerCase()) ||
    e.detail?.toLowerCase().includes(search.toLowerCase())
  );

  function formatTs(ts: string): string {
    try {
      const d = new Date(ts);
      return d.toLocaleString('nl-NL', { dateStyle: 'short', timeStyle: 'medium' });
    } catch { return ts; }
  }

  const ACTION_ICONS: Record<string, string> = {
    scan_started: '▶',
    scan_completed: '✓',
    scan_failed: '✗',
    scan_stopped: '■',
    scan_paused: '⏸',
    scan_resumed: '⏵',
    scan_authorized: '🔒',
    finding_marked: '🏷',
    schedule_created: '📅',
    webhook_created: '🔗',
    api_key_created: '🔑',
    deduplication: '♻',
    settings_saved: '⚙',
  };
</script>

<div class="audit-page">
  <header class="page-header">
    <div>
      <h1>Audit Log</h1>
      <p class="subtitle">Onveranderlijk overzicht van alle systeemacties</p>
    </div>
    <button class="btn-secondary" on:click={reload}>↻ Vernieuwen</button>
  </header>

  <div class="toolbar">
    <input class="search-input" type="text" placeholder="Zoek op actie of detail…" bind:value={search} />
    <span class="count">{filtered.length} van {log.length} entries</span>
  </div>

  {#if error}
    <div class="error-msg">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Laden…</div>
  {:else if filtered.length === 0}
    <div class="empty">Geen audit entries gevonden.</div>
  {:else}
    <div class="log-table">
      <div class="log-header">
        <span class="col-action">Actie</span>
        <span class="col-detail">Detail</span>
        <span class="col-ts">Tijdstip</span>
      </div>
      {#each filtered as entry, i}
        <div class="log-row" class:even={i % 2 === 0}>
          <span class="col-action">
            <span class="action-icon">{ACTION_ICONS[entry.action] ?? '•'}</span>
            <span class="action-name">{entry.action?.replace(/_/g, ' ')}</span>
          </span>
          <span class="col-detail muted">{entry.detail || '—'}</span>
          <span class="col-ts muted mono">{formatTs(entry.ts)}</span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .audit-page { padding: 2rem; max-width: 1000px; }
  .page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .subtitle { color: var(--text-muted, #888); font-size: 0.85rem; margin: 0.25rem 0 0; }
  .btn-secondary { background: none; border: 1px solid var(--border, #444); color: var(--text-muted, #aaa);
                   padding: 0.4rem 1rem; cursor: pointer; font-size: 0.875rem; }
  .btn-secondary:hover { border-color: var(--highlight, #0ff); color: var(--text, #fff); }
  .toolbar { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.25rem; }
  .search-input {
    background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.4rem 0.75rem; font-size: 0.875rem; width: 300px;
  }
  .count { font-size: 0.8rem; color: var(--text-muted, #888); }
  .log-table { display: flex; flex-direction: column; font-size: 0.85rem; }
  .log-header {
    display: grid; grid-template-columns: 200px 1fr 180px;
    padding: 0.5rem 0.75rem; border-bottom: 2px solid var(--border, #333);
    font-size: 0.75rem; font-weight: 600; color: var(--text-muted, #888); text-transform: uppercase;
  }
  .log-row {
    display: grid; grid-template-columns: 200px 1fr 180px;
    padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--border, #1a1a1a);
    align-items: center;
  }
  .log-row.even { background: var(--surface, #0f0f0f); }
  .col-action { display: flex; align-items: center; gap: 0.5rem; }
  .action-icon { font-size: 0.9rem; width: 1.2rem; text-align: center; }
  .action-name { text-transform: capitalize; }
  .col-detail { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .muted { color: var(--text-muted, #888); }
  .mono { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
  .loading, .empty { color: var(--text-muted, #888); text-align: center; padding: 3rem; }
  .error-msg { color: #ff4444; padding: 0.75rem; border: 1px solid #ff4444; margin-bottom: 1rem; }
</style>
