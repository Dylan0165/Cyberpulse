<script lang="ts">
  import { onMount } from 'svelte';
  import { getRecentScans, getComplianceScore, getComplianceMapping } from '../lib/api';

  let scans: any[] = [];
  let selectedScan = '';
  let compliance: any = null;
  let mapping: any = null;
  let loading = false;
  let error = '';

  const OWASP_COLORS: Record<string, string> = {
    'A01:2021': '#ff4444', 'A02:2021': '#ff8c00', 'A03:2021': '#ff4444',
    'A04:2021': '#ffd700', 'A05:2021': '#ff8c00', 'A06:2021': '#ff8c00',
    'A07:2021': '#ff4444', 'A08:2021': '#ffd700', 'A09:2021': '#aaa',
    'A10:2021': '#ff8c00',
  };

  onMount(async () => {
    [scans, mapping] = await Promise.all([getRecentScans(30), getComplianceMapping().catch(() => null)]);
    if (scans.length > 0) {
      selectedScan = scans[0].scan_id;
      await load();
    }
  });

  async function load() {
    if (!selectedScan) return;
    loading = true; error = '';
    try {
      compliance = await getComplianceScore(selectedScan);
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  $: top10 = compliance?.owasp_top10 ?? [];
  $: found = compliance?.owasp_findings ?? {};
  $: coveragePct = compliance?.coverage_pct ?? 0;
</script>

<div class="compliance-page">
  <header class="page-header">
    <div>
      <h1>Compliance &amp; Mapping</h1>
      <p class="subtitle">OWASP Top 10 • CWE • MITRE ATT&amp;CK • NIS2 • ISO 27001</p>
    </div>
    <div class="scan-select-wrap">
      <select bind:value={selectedScan} on:change={load}>
        {#each scans as s}
          <option value={s.scan_id}>{s.target} – {s.scan_type} ({s.scan_id?.slice(0, 8)})</option>
        {/each}
      </select>
    </div>
  </header>

  {#if error}
    <div class="error-msg">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Laden…</div>
  {:else if compliance}
    <!-- Coverage summary -->
    <div class="summary-row">
      <div class="summary-card">
        <span class="label">OWASP Categorieën</span>
        <span class="value {compliance.owasp_categories_found > 3 ? 'bad' : 'good'}">
          {compliance.owasp_categories_found} / 10
        </span>
      </div>
      <div class="summary-card">
        <span class="label">Dekking</span>
        <span class="value">{coveragePct}%</span>
      </div>
    </div>

    <!-- OWASP Top 10 grid -->
    <section class="section">
      <h2>OWASP Top 10 (2021)</h2>
      <div class="owasp-grid">
        {#each top10 as cat}
          {@const hits = found[cat.id] ?? []}
          <div class="owasp-card {hits.length > 0 ? 'affected' : 'clean'}">
            <div class="owasp-id" style="color:{OWASP_COLORS[cat.id] ?? '#888'}">{cat.id}</div>
            <div class="owasp-name">{cat.name}</div>
            {#if hits.length > 0}
              <div class="hits">
                {#each hits as hit}
                  <div class="hit-row">
                    <span class="cwe-tag">{hit.cwe}</span>
                    {#if hit.mitre}
                      <span class="mitre-tag">ATT&CK {hit.mitre}</span>
                    {/if}
                    <span class="hit-label">{hit.label}</span>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="clean-label">Niet aangetroffen</div>
            {/if}
          </div>
        {/each}
      </div>
    </section>

    <!-- Regulatory notes -->
    <section class="section">
      <h2>Regelgeving</h2>
      <div class="reg-cards">
        <div class="reg-card">
          <h3>NIS2</h3>
          <p>{compliance.nis2_note}</p>
        </div>
        <div class="reg-card">
          <h3>ISO 27001</h3>
          <p>{compliance.iso27001_note}</p>
        </div>
        <div class="reg-card">
          <h3>GDPR</h3>
          <p>Artikel 32: Passende technische maatregelen zijn verplicht voor bescherming van persoonsgegevens. Kwetsbaarheden kunnen meldingsplicht activeren.</p>
        </div>
      </div>
    </section>
  {:else if !loading && scans.length === 0}
    <div class="empty-state">Start eerst een scan om compliance data te zien.</div>
  {/if}
</div>

<style>
  .compliance-page { padding: 2rem; max-width: 1100px; }
  .page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .subtitle { color: var(--text-muted, #888); font-size: 0.8rem; margin: 0.25rem 0 0; }
  .scan-select-wrap select {
    background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.3rem 0.75rem; font-size: 0.875rem; max-width: 360px;
  }
  .summary-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
  .summary-card { background: var(--surface, #111); border: 1px solid var(--border, #333);
                  padding: 1rem 1.5rem; display: flex; flex-direction: column; gap: 0.25rem; }
  .summary-card .label { font-size: 0.75rem; color: var(--text-muted, #888); text-transform: uppercase; }
  .summary-card .value { font-size: 1.75rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
  .value.bad { color: #ff4444; }
  .value.good { color: #00cc66; }
  .section { margin-bottom: 2.5rem; }
  .section h2 { font-size: 1rem; font-weight: 700; margin: 0 0 1rem; border-bottom: 1px solid var(--border, #333); padding-bottom: 0.5rem; }
  .owasp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.75rem; }
  .owasp-card { background: var(--surface, #111); border: 1px solid var(--border, #222);
                padding: 1rem; display: flex; flex-direction: column; gap: 0.4rem; }
  .owasp-card.affected { border-color: #ff4444; }
  .owasp-card.clean { opacity: 0.6; }
  .owasp-id { font-size: 0.75rem; font-weight: 700; font-family: monospace; }
  .owasp-name { font-size: 0.8rem; font-weight: 600; line-height: 1.3; }
  .hits { display: flex; flex-direction: column; gap: 0.3rem; margin-top: 0.25rem; }
  .hit-row { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; }
  .cwe-tag { background: rgba(255,140,0,.15); color: #ff8c00; border: 1px solid #ff8c00;
             padding: 0.1rem 0.4rem; font-size: 0.7rem; font-family: monospace; }
  .mitre-tag { background: rgba(100,149,237,.15); color: #6495ed; border: 1px solid #6495ed;
               padding: 0.1rem 0.4rem; font-size: 0.7rem; font-family: monospace; }
  .hit-label { font-size: 0.75rem; color: var(--text-muted, #bbb); }
  .clean-label { font-size: 0.75rem; color: #00cc66; }
  .reg-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
  .reg-card { background: var(--surface, #111); border: 1px solid var(--border, #333); padding: 1.25rem; }
  .reg-card h3 { font-size: 0.9rem; font-weight: 700; margin: 0 0 0.75rem; color: var(--highlight, #0ff); }
  .reg-card p { font-size: 0.825rem; color: var(--text-muted, #aaa); line-height: 1.5; margin: 0; }
  .loading, .empty-state { color: var(--text-muted, #888); padding: 3rem; text-align: center; }
  .error-msg { color: #ff4444; padding: 0.75rem; border: 1px solid #ff4444; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
