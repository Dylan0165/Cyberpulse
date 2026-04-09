<script lang="ts">
  import { onMount } from 'svelte';
  import { getAssets } from '../lib/api';

  let assets: any[] = [];
  let loading = true;
  let error = '';
  let search = '';
  let sortCol = 'risk_score';
  let sortDir: 'asc' | 'desc' = 'desc';

  onMount(async () => {
    try {
      assets = await getAssets();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  $: filtered = assets.filter(a =>
    a.target.toLowerCase().includes(search.toLowerCase()) ||
    (a.os_guess || '').toLowerCase().includes(search.toLowerCase())
  );

  $: sorted = [...filtered].sort((a, b) => {
    const va = a[sortCol] ?? 0;
    const vb = b[sortCol] ?? 0;
    return sortDir === 'desc' ? (va < vb ? 1 : -1) : (va > vb ? 1 : -1);
  });

  function sort(col: string) {
    if (sortCol === col) {
      sortDir = sortDir === 'desc' ? 'asc' : 'desc';
    } else {
      sortCol = col;
      sortDir = 'desc';
    }
  }

  function riskClass(score: number | null): string {
    if (score === null) return 'unknown';
    if (score >= 80) return 'critical';
    if (score >= 60) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  }

  function formatDate(ts: string | null): string {
    if (!ts) return '—';
    try { return new Date(ts).toLocaleDateString('nl-NL'); } catch { return ts; }
  }
</script>

<div class="assets-page">
  <header class="page-header">
    <h1>Asset Inventaris</h1>
    <p class="subtitle">{assets.length} ontdekte assets</p>
  </header>

  <div class="toolbar">
    <input
      class="search-input"
      type="text"
      placeholder="Zoek op target of OS..."
      bind:value={search}
    />
  </div>

  {#if loading}
    <div class="loading">Laden…</div>
  {:else if error}
    <div class="error-msg">{error}</div>
  {:else if sorted.length === 0}
    <div class="empty-state">
      <p>Nog geen assets gevonden. Start eerste een scan om assets te ontdekken.</p>
    </div>
  {:else}
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th class="sortable" on:click={() => sort('target')}>
              Target {sortCol === 'target' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
            </th>
            <th>Poorten</th>
            <th>OS</th>
            <th class="sortable" on:click={() => sort('scan_count')}>
              Scans {sortCol === 'scan_count' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
            </th>
            <th class="sortable" on:click={() => sort('total_findings')}>
              Bevindingen {sortCol === 'total_findings' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
            </th>
            <th class="sortable" on:click={() => sort('risk_score')}>
              Risicoscore {sortCol === 'risk_score' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
            </th>
            <th>Laatste scan</th>
          </tr>
        </thead>
        <tbody>
          {#each sorted as asset (asset.target)}
            <tr>
              <td class="target-cell">
                <span class="target-icon">{asset.target_type === 'network' ? '🔌' : '🌐'}</span>
                <span>{asset.target}</span>
              </td>
              <td class="ports-cell">
                {#if asset.open_ports && asset.open_ports.length > 0}
                  {#each asset.open_ports.slice(0, 6) as port}
                    <span class="port-badge">{port}</span>
                  {/each}
                  {#if asset.open_ports.length > 6}
                    <span class="port-more">+{asset.open_ports.length - 6}</span>
                  {/if}
                {:else}
                  <span class="muted">—</span>
                {/if}
              </td>
              <td>{#if asset.os_guess}{asset.os_guess}{:else}<span class="muted">—</span>{/if}</td>
              <td class="center">{asset.scan_count}</td>
              <td class="center">{asset.total_findings || 0}</td>
              <td>
                <span class="risk-badge {riskClass(asset.risk_score)}">
                  {asset.risk_score !== null ? `${asset.risk_score}/100` : '—'}
                </span>
              </td>
              <td class="muted">{formatDate(asset.last_scan)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .assets-page { padding: 2rem; max-width: 1200px; }
  .page-header { margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .subtitle { color: var(--text-muted, #888); font-size: 0.85rem; margin: 0.25rem 0 0; }
  .toolbar { margin-bottom: 1.25rem; }
  .search-input {
    background: var(--surface, #1a1a1a); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.5rem 1rem; font-size: 0.9rem; width: 320px;
    outline: none;
  }
  .search-input:focus { border-color: var(--accent, #0ff); }
  .table-wrapper { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th { text-align: left; padding: 0.75rem 1rem; background: var(--surface, #1a1a1a);
       border-bottom: 2px solid var(--border, #333); color: var(--text-muted, #888);
       font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
  th.sortable { cursor: pointer; }
  th.sortable:hover { color: var(--text, #fff); }
  td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border, #222); vertical-align: middle; }
  tr:hover td { background: var(--surface, #111); }
  .target-cell { display: flex; align-items: center; gap: 0.5rem; font-weight: 500; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
  .ports-cell { display: flex; flex-wrap: wrap; gap: 0.25rem; }
  .port-badge { background: var(--surface, #222); border: 1px solid var(--border, #333);
                padding: 0.1rem 0.4rem; font-size: 0.75rem; font-family: monospace; }
  .port-more { color: var(--text-muted, #888); font-size: 0.75rem; }
  .center { text-align: center; }
  .muted { color: var(--text-muted, #888); }
  .risk-badge { display: inline-block; padding: 0.2rem 0.6rem; font-size: 0.75rem; font-weight: 700; font-family: monospace; }
  .risk-badge.critical { background: rgba(255,0,0,.15); color: #ff4444; border: 1px solid #ff4444; }
  .risk-badge.high { background: rgba(255,140,0,.15); color: #ff8c00; border: 1px solid #ff8c00; }
  .risk-badge.medium { background: rgba(255,215,0,.15); color: #ffd700; border: 1px solid #ffd700; }
  .risk-badge.low { background: rgba(0,255,0,.1); color: #00cc66; border: 1px solid #00cc66; }
  .risk-badge.unknown { background: var(--surface, #222); color: var(--text-muted, #888); border: 1px solid var(--border, #333); }
  .loading, .empty-state { color: var(--text-muted, #888); padding: 3rem; text-align: center; }
  .error-msg { color: #ff4444; padding: 1rem; border: 1px solid #ff4444; }
</style>
