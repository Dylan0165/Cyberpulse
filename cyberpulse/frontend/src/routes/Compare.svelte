<script lang="ts">
  import { onMount } from 'svelte';
  import { getRecentScans, compareScans } from '../lib/api';

  let scans: any[] = [];
  let scanA = '';
  let scanB = '';
  let result: any = null;
  let loading = false;
  let error = '';
  let activeTab: 'new' | 'resolved' | 'unchanged' = 'new';

  onMount(async () => {
    scans = await getRecentScans(50);
    if (scans.length >= 2) {
      scanA = scans[1].scan_id;
      scanB = scans[0].scan_id;
    }
  });

  async function compare() {
    if (!scanA || !scanB || scanA === scanB) return;
    loading = true; error = ''; result = null;
    try {
      result = await compareScans(scanA, scanB);
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function scanLabel(id: string): string {
    const s = scans.find(x => x.scan_id === id);
    return s ? `${s.target} (${id.slice(0, 8)})` : id.slice(0, 16);
  }

  function sevClass(s: string): string {
    return s?.toLowerCase() ?? 'info';
  }
</script>

<div class="compare-page">
  <header class="page-header">
    <h1>Scan Vergelijken</h1>
    <p class="subtitle">Delta analyse — nieuwe, opgeloste en ongewijzigde bevindingen</p>
  </header>

  <div class="select-bar">
    <div class="select-group">
      <label>Baseline scan (oud)</label>
      <select bind:value={scanA}>
        {#each scans as s}
          <option value={s.scan_id}>{s.target} – {s.scan_type} – {s.scan_id?.slice(0, 10)}</option>
        {/each}
      </select>
    </div>
    <div class="arrow">→</div>
    <div class="select-group">
      <label>Nieuwe scan</label>
      <select bind:value={scanB}>
        {#each scans as s}
          <option value={s.scan_id}>{s.target} – {s.scan_type} – {s.scan_id?.slice(0, 10)}</option>
        {/each}
      </select>
    </div>
    <button class="btn-primary" on:click={compare} disabled={!scanA || !scanB || scanA === scanB || loading}>
      {loading ? 'Vergelijken…' : 'Vergelijk'}
    </button>
  </div>

  {#if error}
    <div class="error-msg">{error}</div>
  {/if}

  {#if result}
    <!-- Summary cards -->
    <div class="summary-row">
      <button class="summary-card new" class:active={activeTab === 'new'} on:click={() => activeTab = 'new'}>
        <span class="count">{result.summary.new_count}</span>
        <span class="label">Nieuw</span>
      </button>
      <button class="summary-card resolved" class:active={activeTab === 'resolved'} on:click={() => activeTab = 'resolved'}>
        <span class="count">{result.summary.resolved_count}</span>
        <span class="label">Opgelost</span>
      </button>
      <button class="summary-card unchanged" class:active={activeTab === 'unchanged'} on:click={() => activeTab = 'unchanged'}>
        <span class="count">{result.summary.unchanged_count}</span>
        <span class="label">Ongewijzigd</span>
      </button>
    </div>

    <!-- Tab content -->
    <div class="findings-list">
      {#if activeTab === 'new'}
        {#if result.new.length === 0}
          <div class="empty-tab">Geen nieuwe bevindingen — uitstekend! ✓</div>
        {:else}
          {#each result.new as f}
            <div class="finding-row">
              <span class="sev sev-{sevClass(f.severity)}">{f.severity}</span>
              <span class="ftype mono">{f.type || 'bevinding'}</span>
              <span class="fdesc">{f.title || f.beschrijving || '—'}</span>
              {#if f.target || f.url}
                <span class="ftarget muted">{f.target || f.url}</span>
              {/if}
            </div>
          {/each}
        {/if}
      {:else if activeTab === 'resolved'}
        {#if result.resolved.length === 0}
          <div class="empty-tab">Geen opgeloste bevindingen.</div>
        {:else}
          {#each result.resolved as f}
            <div class="finding-row resolved-row">
              <span class="sev sev-{sevClass(f.severity)}">{f.severity}</span>
              <span class="ftype mono">{f.type || 'bevinding'}</span>
              <span class="fdesc">{f.title || f.beschrijving || '—'}</span>
              <span class="resolved-tag">✓ Opgelost</span>
            </div>
          {/each}
        {/if}
      {:else}
        {#if result.unchanged.length === 0}
          <div class="empty-tab">Geen ongewijzigde bevindingen.</div>
        {:else}
          {#each result.unchanged as f}
            <div class="finding-row">
              <span class="sev sev-{sevClass(f.severity)}">{f.severity}</span>
              <span class="ftype mono">{f.type || 'bevinding'}</span>
              <span class="fdesc">{f.title || f.beschrijving || '—'}</span>
            </div>
          {/each}
        {/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  .compare-page { padding: 2rem; max-width: 1000px; }
  .page-header { margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .subtitle { color: var(--text-muted, #888); font-size: 0.85rem; margin: 0.25rem 0 0; }
  .select-bar { display: flex; align-items: flex-end; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
  .select-group { display: flex; flex-direction: column; gap: 0.375rem; }
  .select-group label { font-size: 0.75rem; color: var(--text-muted, #888); text-transform: uppercase; }
  .select-group select {
    background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.4rem 0.75rem; font-size: 0.875rem;
  }
  .arrow { font-size: 1.5rem; color: var(--text-muted, #666); padding-bottom: 0.25rem; }
  .btn-primary { background: var(--surface, #1a1a1a); border: 1px solid var(--border, #444);
                 color: var(--text, #fff); padding: 0.5rem 1.5rem; cursor: pointer; font-size: 0.875rem; }
  .btn-primary:hover:not(:disabled) { border-color: var(--highlight, #0ff); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .summary-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
  .summary-card {
    flex: 1; padding: 1rem 1.5rem; display: flex; flex-direction: column; align-items: center;
    gap: 0.25rem; border: 1px solid var(--border, #333); background: var(--surface, #111);
    cursor: pointer; transition: border-color 0.15s;
  }
  .summary-card.active.new { border-color: #ff4444; }
  .summary-card.active.resolved { border-color: #00cc66; }
  .summary-card.active.unchanged { border-color: #888; }
  .summary-card .count { font-size: 2rem; font-weight: 700; font-family: monospace; }
  .summary-card.new .count { color: #ff4444; }
  .summary-card.resolved .count { color: #00cc66; }
  .summary-card.unchanged .count { color: #888; }
  .summary-card .label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted, #888); }
  .findings-list { display: flex; flex-direction: column; gap: 0.5rem; }
  .finding-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 1rem;
                 background: var(--surface, #111); border: 1px solid var(--border, #222); flex-wrap: wrap; }
  .resolved-row { opacity: 0.65; }
  .sev { display: inline-block; padding: 0.15rem 0.5rem; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
  .sev-critical { background: rgba(255,0,0,.15); color: #ff4444; border: 1px solid #ff4444; }
  .sev-high { background: rgba(255,140,0,.15); color: #ff8c00; border: 1px solid #ff8c00; }
  .sev-medium { background: rgba(255,215,0,.15); color: #ffd700; border: 1px solid #ffd700; }
  .sev-low { background: rgba(0,200,100,.1); color: #00cc66; border: 1px solid #00cc66; }
  .sev-info { background: var(--surface, #222); color: #888; border: 1px solid #444; }
  .ftype { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #0ff; }
  .fdesc { font-size: 0.875rem; flex: 1; }
  .ftarget { font-size: 0.75rem; font-family: monospace; }
  .muted { color: var(--text-muted, #888); }
  .mono { font-family: monospace; }
  .resolved-tag { font-size: 0.75rem; color: #00cc66; }
  .empty-tab { color: var(--text-muted, #888); text-align: center; padding: 2rem; }
  .error-msg { color: #ff4444; padding: 0.75rem; border: 1px solid #ff4444; margin-bottom: 1rem; }
</style>
