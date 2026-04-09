<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { getReport, downloadPdf } from '../lib/api';

  export let scanId: string;
  const dispatch = createEventDispatcher();

  let report: any = null;
  let loading = true;
  let error = '';
  let showAllFindings = false;
  let filterSeverity = 'all';
  let expandedIdx: number | null = null;
  let searchQuery = '';

  onMount(async () => {
    window.addEventListener('keydown', handleKey);
    try {
      const raw = await getReport(scanId);

      // Aggregate raw findings from all modules
      const rawFindings: any[] = [];
      for (const mod of (raw.scan_data?.results ?? [])) {
        for (const f of (mod.findings ?? [])) {
          rawFindings.push({
            ...f,
            _module: mod.module_id ?? mod.name ?? '?',
            _module_name: mod.name ?? mod.module_id ?? '?',
          });
        }
      }

      // Sort by severity
      rawFindings.sort((a, b) => severityOrder(a.severity ?? a.ernst ?? 'info') - severityOrder(b.severity ?? b.ernst ?? 'info'));

      const hasAnalysis = raw.analysis && Object.keys(raw.analysis).length > 0;

      report = {
        target: raw.scan_data?.target ?? scanId,
        scan_type: raw.scan_data?.scan_type ?? '',
        scan_mode: raw.scan_data?.scan_mode ?? '',
        modules_count: raw.scan_data?.modules_run?.length ?? 0,
        generated_at: raw.scan_data?.started_at ?? '',
        total_findings: raw.scan_data?.total_findings ?? rawFindings.length,
        raw_findings: rawFindings,

        // AI analysis fields (may be empty)
        has_analysis: hasAnalysis,
        risicoscore: raw.analysis?.samenvatting?.risicoscore ?? null,
        management_samenvatting: raw.analysis?.management_samenvatting ?? '',
        bevindingen: raw.analysis?.bevindingen ?? [],
        aanbevelingen_prioriteit: raw.analysis?.aanbevelingen_prioriteit ?? [],
        technische_details: raw.analysis?.technische_details ?? '',
      };
    } catch (e: any) {
      error = e.message || 'Rapport laden mislukt';
    }
    loading = false;
    return () => window.removeEventListener('keydown', handleKey);
  });

  function riskClass(score: number): string {
    if (score >= 80) return 'critical';
    if (score >= 60) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  }

  function riskLabel(score: number): string {
    if (score >= 80) return 'KRITIEK RISICO';
    if (score >= 60) return 'HOOG RISICO';
    if (score >= 40) return 'GEMIDDELD RISICO';
    if (score >= 20) return 'LAAG RISICO';
    return 'VEILIG';
  }

  async function handleDownloadPdf() {
    try {
      const blob = await downloadPdf(scanId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cyberpulse-${scanId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('PDF download failed:', e);
    }
  }

  function severityOrder(sev: string): number {
    return { critical: 0, high: 1, medium: 2, low: 3, info: 4 }[sev?.toLowerCase()] ?? 5;
  }

  function countBySev(sev: string): number {
    return report?.raw_findings?.filter((f: any) => (f.severity ?? f.ernst ?? 'info').toLowerCase() === sev).length ?? 0;
  }

  function findingLabel(f: any): string {
    return f.title ?? f.titel ?? f.type ?? f.name ?? 'Bevinding';
  }

  function findingDesc(f: any): string {
    return f.description ?? f.beschrijving ?? f.detail ?? f.banner ?? '';
  }

  function findingSev(f: any): string {
    return (f.severity ?? f.ernst ?? 'info').toLowerCase();
  }

  $: filteredFindings = report?.raw_findings?.filter((f: any) =>
    (filterSeverity === 'all' || findingSev(f) === filterSeverity) &&
    (!searchQuery || findingLabel(f).toLowerCase().includes(searchQuery.toLowerCase()) ||
     findingDesc(f).toLowerCase().includes(searchQuery.toLowerCase()) ||
     (f._module ?? '').toLowerCase().includes(searchQuery.toLowerCase()))
  ) ?? [];

  $: displayedFindings = showAllFindings ? filteredFindings : filteredFindings.slice(0, 100);

  function toggleExpand(idx: number) {
    expandedIdx = expandedIdx === idx ? null : idx;
  }

  function exportCsv() {
    if (!report?.raw_findings?.length) return;
    const headers = ['Severity', 'Module', 'Title', 'Description', 'Detail'];
    const rows = report.raw_findings.map((f: any) => [
      findingSev(f),
      f._module ?? '',
      findingLabel(f),
      String(findingDesc(f) ?? '').replace(/"/g, '""'),
      String(f.detail ?? f.banner ?? f.raw ?? '').replace(/"/g, '""'),
    ].map((v: string) => `"${v}"`).join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cyberpulse-${scanId}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Escape') dispatch('navigate', '/');
    if (e.key === 'p' || e.key === 'P') handleDownloadPdf();
    if (e.key === 'x' || e.key === 'X') exportCsv();
  }
</script>

<div class="page-header">
  <h1 class="page-title">Rapport — {report?.target || scanId.slice(0, 15)}</h1>
  <div style="display: flex; gap: var(--space-2);">
    <button class="btn" on:click={exportCsv} title="Exporteer als CSV (X)">CSV</button>
    <button class="btn" on:click={handleDownloadPdf} title="Download PDF (P)">PDF</button>
    <button class="btn" on:click={() => dispatch('navigate', '/scan/new')}>Opnieuw</button>
    <button class="btn" on:click={() => dispatch('navigate', '/')} title="Terug (Esc)">← Terug</button>
  </div>
</div>

{#if loading}
  <p style="color: var(--text-2);">Laden...</p>
{:else if error}
  <p style="color: var(--critical);">{error}</p>
{:else if report}

  <!-- Header kaart: score of telling -->
  <div class="card" style="display: flex; align-items: center; gap: var(--space-6); padding: var(--space-5);">
    {#if report.has_analysis && report.risicoscore !== null}
      <div style="text-align: center; min-width: 100px;">
        <div class="risk-score {riskClass(report.risicoscore)}">{report.risicoscore}</div>
        <div style="font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-2); margin-top: 4px;">
          {riskLabel(report.risicoscore)}
        </div>
      </div>
    {:else}
      <div style="text-align: center; min-width: 100px;">
        <div style="font-size: 11px; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.08em;">Geen AI analyse</div>
        <div style="font-size: 11px; color: var(--text-2); margin-top: 4px;">Stel een DeepSeek API-key in</div>
      </div>
    {/if}

    <div style="flex: 1; display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px; background: var(--border);">
      {#each ['critical','high','medium','low','info'] as sev}
        <div style="background: var(--bg-2); padding: var(--space-3); text-align: center; cursor: pointer;"
             on:click={() => filterSeverity = filterSeverity === sev ? 'all' : sev}
             on:keydown={() => {}}
             class:active-filter={filterSeverity === sev}>
          <div style="font-size: 20px; font-weight: 700; color: var(--{sev === 'info' ? 'text-3' : sev === 'low' ? 'text-2' : sev});">
            {countBySev(sev)}
          </div>
          <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3);">{sev}</div>
        </div>
      {/each}
    </div>

    <div style="font-size: 11px; color: var(--text-3); text-align: right; white-space: nowrap;">
      <div>{report.total_findings} bevindingen</div>
      <div>{report.modules_count} modules</div>
      <div>{report.scan_type} / {report.scan_mode}</div>
      {#if report.generated_at}
        <div>{new Date(report.generated_at).toLocaleString('nl-NL')}</div>
      {/if}
    </div>
  </div>

  <!-- AI samenvatting (alleen als beschikbaar) -->
  {#if report.management_samenvatting}
    <div class="card">
      <div class="card-header">
        <span class="card-title">AI Samenvatting</span>
      </div>
      <p style="font-family: var(--font-read); font-size: 14px; line-height: 1.8; color: var(--text);">
        {report.management_samenvatting}
      </p>
    </div>
  {/if}

  <!-- Aanbevelingen (AI) -->
  {#if report.aanbevelingen_prioriteit?.length > 0}
    <div class="card">
      <div class="card-header">
        <span class="card-title">AI Aanbevelingen</span>
        <span class="card-title">{report.aanbevelingen_prioriteit.length} acties</span>
      </div>
      {#each report.aanbevelingen_prioriteit as r, i}
        <div style="display: flex; gap: var(--space-3); padding: var(--space-2) 0; border-bottom: 1px solid var(--border);">
          <div style="font-size: 18px; font-weight: 700; color: var(--text-3); min-width: 30px; line-height: 1.4;">{r.prioriteit ?? i + 1}</div>
          <div>
            <div style="font-weight: 700; font-size: 13px;">{r.actie}</div>
            {#if r.reden}<div style="font-size: 11px; color: var(--text-2); margin-top: 2px;">{r.reden}</div>{/if}
            {#if r.complexiteit}<div style="font-size: 10px; color: var(--text-3); margin-top: 2px;">Complexiteit: {r.complexiteit}</div>{/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Alle raw bevindingen -->
  <div class="card">
    <div class="card-header">
      <span class="card-title">
        Bevindingen
        {#if filterSeverity !== 'all'}<span style="color: var(--text-2);"> — filter: {filterSeverity}</span>{/if}
      </span>
      <div style="display: flex; gap: var(--space-2); align-items: center;">
        <span class="card-title">{filteredFindings.length} / {report.total_findings}</span>
        {#if filterSeverity !== 'all'}
          <button class="btn" style="font-size: 10px; padding: 2px 6px;" on:click={() => filterSeverity = 'all'}>× Reset</button>
        {/if}
      </div>
    </div>

    <!-- Search bar -->
    <div style="padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--border);">
      <input
        type="text"
        placeholder="Zoek bevindingen… (titel, module, beschrijving)"
        bind:value={searchQuery}
        style="width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 6px 10px; font-family: var(--font-mono); font-size: 12px; outline: none;"
      />
    </div>

    {#if filteredFindings.length === 0}
      <p style="color: var(--text-3); padding: var(--space-3);">Geen bevindingen voor dit filter.</p>
    {:else}
      <table class="findings-table">
        <thead>
          <tr>
            <th style="width: 80px;">Ernst</th>
            <th>Bevinding</th>
            <th style="width: 60px;">Module</th>
          </tr>
        </thead>
        <tbody>
          {#each displayedFindings as f, idx}
            <tr
              class="finding-row"
              class:expanded={expandedIdx === idx}
              on:click={() => toggleExpand(idx)}
              on:keydown={(e) => e.key === 'Enter' && toggleExpand(idx)}
              tabindex="0"
              style="cursor: pointer;"
            >
              <td><span class="badge badge-{findingSev(f)}">{findingSev(f)}</span></td>
              <td>
                <div class="finding-title">{findingLabel(f)}</div>
                {#if findingDesc(f)}
                  <div class="finding-desc">{String(findingDesc(f)).slice(0, 120)}</div>
                {/if}
              </td>
              <td style="color: var(--text-3); font-size: 11px;">{f._module}</td>
            </tr>
            {#if expandedIdx === idx}
              <tr class="finding-detail-row">
                <td colspan="3" style="padding: 0;">
                  <div class="finding-detail">
                    <div class="detail-grid">
                      {#if findingLabel(f) !== findingDesc(f) && findingDesc(f)}
                        <div class="detail-item">
                          <span class="detail-label">Beschrijving</span>
                          <span class="detail-value">{findingDesc(f)}</span>
                        </div>
                      {/if}
                      {#if f.detail && f.detail !== findingDesc(f)}
                        <div class="detail-item">
                          <span class="detail-label">Detail</span>
                          <span class="detail-value">{f.detail}</span>
                        </div>
                      {/if}
                      {#if f.banner}
                        <div class="detail-item">
                          <span class="detail-label">Banner</span>
                          <span class="detail-value">{f.banner}</span>
                        </div>
                      {/if}
                      {#if f.url}
                        <div class="detail-item">
                          <span class="detail-label">URL</span>
                          <span class="detail-value">{f.url}</span>
                        </div>
                      {/if}
                      {#if f.port}
                        <div class="detail-item">
                          <span class="detail-label">Port</span>
                          <span class="detail-value">{f.port}{f.protocol ? ` / ${f.protocol}` : ''}</span>
                        </div>
                      {/if}
                      {#if f.cve}
                        <div class="detail-item">
                          <span class="detail-label">CVE</span>
                          <span class="detail-value" style="color: var(--critical);">{f.cve}</span>
                        </div>
                      {/if}
                      {#if f.impact ?? f.aanbeveling}
                        {#if f.impact}
                          <div class="detail-item">
                            <span class="detail-label">Impact</span>
                            <span class="detail-value">{f.impact}</span>
                          </div>
                        {/if}
                        {#if f.aanbeveling}
                          <div class="detail-item">
                            <span class="detail-label">Aanbeveling</span>
                            <span class="detail-value" style="color: var(--info);">{f.aanbeveling}</span>
                          </div>
                        {/if}
                      {/if}
                      <div class="detail-item">
                        <span class="detail-label">Module</span>
                        <span class="detail-value">{f._module_name ?? f._module}</span>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>

      {#if filteredFindings.length > displayedFindings.length}
        <div style="padding: var(--space-3); text-align: center;">
          <button class="btn" on:click={() => showAllFindings = true}>
            Toon alle {filteredFindings.length} bevindingen
          </button>
        </div>
      {/if}
    {/if}
  </div>

{/if}

<style>
  .active-filter {
    outline: 1px solid var(--border-2);
  }

  .finding-row:hover {
    background: var(--bg-3, rgba(255,255,255,0.04));
  }

  .finding-row:focus {
    outline: 1px solid var(--border-2);
  }

  .finding-row.expanded td {
    border-bottom: none;
  }

  .finding-detail-row td {
    background: var(--bg-3, rgba(255,255,255,0.03));
    border-bottom: 1px solid var(--border);
  }

  .finding-detail {
    padding: var(--space-3) var(--space-4);
  }

  .detail-grid {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .detail-item {
    display: grid;
    grid-template-columns: 110px 1fr;
    gap: var(--space-2);
    font-size: 12px;
    line-height: 1.5;
  }

  .detail-label {
    color: var(--text-3);
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.08em;
    padding-top: 1px;
  }

  .detail-value {
    color: var(--text);
    word-break: break-word;
    font-family: var(--font-mono);
    font-size: 11px;
  }
</style>
