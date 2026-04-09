<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { getRecentScans } from '../lib/api';

  const dispatch = createEventDispatcher();

  let scans: any[] = [];
  let loading = true;
  let search = '';

  onMount(async () => {
    try {
      scans = await getRecentScans(50);
    } catch (e) {
      console.error('Failed to load scans:', e);
    }
    loading = false;
  });

  function riskClass(score: number): string {
    if (score >= 80) return 'critical';
    if (score >= 60) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  }

  function formatDate(iso: string): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('nl-NL', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  function openScan(scan: any) {
    if (scan.has_report || scan.has_analysis || scan.total_findings > 0) {
      dispatch('navigate', `/scan/${scan.scan_id}/report`);
    } else {
      dispatch('navigate', `/scan/${scan.scan_id}/progress`);
    }
  }

  $: totalScans = scans.length;
  $: criticalScans = scans.filter(s => s.risk_score != null && s.risk_score >= 80).length;
  $: totalFindings = scans.reduce((acc, s) => acc + (s.total_findings ?? 0), 0);
  $: filtered = scans.filter(s =>
    !search || s.target?.toLowerCase().includes(search.toLowerCase()) || s.scan_type?.toLowerCase().includes(search.toLowerCase())
  );
</script>

<div class="page-header">
  <h1 class="page-title">Dashboard</h1>
  <button class="btn btn-primary" on:click={() => dispatch('navigate', '/scan/new')}>
    + Nieuwe scan
  </button>
</div>

<!-- Stat cards -->
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--border); margin-bottom: var(--space-4);">
  {#each [
    { label: 'Scans totaal', value: totalScans, color: 'var(--text)' },
    { label: 'Kritieke scans', value: criticalScans, color: 'var(--critical)' },
    { label: 'Bevindingen totaal', value: totalFindings, color: 'var(--high)' },
    { label: 'Modules per scan', value: scans[0]?.modules_count ?? '—', color: 'var(--text-2)' },
  ] as stat}
    <div style="background: var(--bg-2); padding: var(--space-4);">
      <div style="font-size: 28px; font-weight: 700; color: {stat.color}; letter-spacing: -0.02em;">{stat.value}</div>
      <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-3); margin-top: var(--space-1);">{stat.label}</div>
    </div>
  {/each}
</div>

<!-- Scan list -->
<div class="card">
  <div class="card-header">
    <span class="card-title">Scan geschiedenis</span>
    <input
      type="text"
      bind:value={search}
      placeholder="Zoeken..."
      style="width: 200px; padding: 4px 8px; font-size: 11px; background: var(--bg-3); border: 1px solid var(--border); color: var(--text);"
    />
  </div>

  {#if loading}
    <p style="color: var(--text-2); padding: var(--space-3);">Laden...</p>
  {:else if filtered.length === 0}
    <p style="color: var(--text-2); padding: var(--space-3);">
      {search ? 'Geen scans gevonden voor dit zoekterm.' : 'Geen scans gevonden. Start een nieuwe scan om te beginnen.'}
    </p>
  {:else}
    <table class="findings-table">
      <thead>
        <tr>
          <th>Target</th>
          <th>Type</th>
          <th>Score</th>
          <th>Findings</th>
          <th>Datum</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {#each filtered as scan}
          <tr style="cursor: pointer;" on:click={() => openScan(scan)}>
            <td>
              <div class="finding-title">{scan.target}</div>
              <div class="finding-desc">{scan.scan_mode ?? ''} / {scan.target_type ?? ''}</div>
            </td>
            <td style="color: var(--text-2);">{scan.scan_type || '—'}</td>
            <td>
              {#if scan.risk_score != null}
                <span class="badge badge-{riskClass(scan.risk_score)}">{scan.risk_score}</span>
              {:else}
                <span style="color: var(--text-3);">—</span>
              {/if}
            </td>
            <td>
              {#if scan.total_findings > 0}
                <span style="font-weight: 700; color: var(--text);">{scan.total_findings}</span>
              {:else}
                <span style="color: var(--text-3);">0</span>
              {/if}
            </td>
            <td style="color: var(--text-2); font-size: 11px;">{formatDate(scan.started_at)}</td>
            <td>
              {#if scan.has_analysis}
                <span style="color: var(--text-2);">✓ AI analyse</span>
              {:else if scan.has_report}
                <span style="color: var(--text-2);">Klaar</span>
              {:else if scan.total_findings > 0}
                <span style="color: var(--accent);">Geen analyse</span>
              {:else}
                <span style="color: var(--text-3);">Bezig...</span>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>
