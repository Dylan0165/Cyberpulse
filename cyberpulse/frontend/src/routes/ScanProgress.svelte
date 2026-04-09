<script lang="ts">
  import { onMount, onDestroy, afterUpdate, createEventDispatcher } from 'svelte';
  import { createScanStream, stopScan } from '../lib/api';
  import type { ScanEvent } from '../lib/stores';

  export let scanId: string;
  const dispatch = createEventDispatcher();

  let modules: Record<string, 'queued' | 'running' | 'done' | 'error'> = {};
  let totalModules = 0;
  let completedModules = 0;
  let liveFindings: { module: string; name: string; count: number }[] = [];
  let totalLiveFindings = 0;
  let logLines: string[] = [];
  let eventSource: EventSource | null = null;
  let analysisStarted = false;
  let done = false;
  let stopping = false;
  let terminalEl: HTMLElement;
  let startTime = Date.now();
  let elapsed = '0:00';
  let timer: ReturnType<typeof setInterval>;

  onMount(() => {
    timer = setInterval(() => {
      const s = Math.floor((Date.now() - startTime) / 1000);
      elapsed = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
    }, 1000);

    eventSource = createScanStream(scanId);

    eventSource.onmessage = (e) => {
      const data: ScanEvent = JSON.parse(e.data);

      switch (data.type) {
        case 'scan_start':
          totalModules = (data as any).total_modules || (data as any).total || 0;
          logLines = [...logLines, `► Scan gestart — ${(data as any).target || scanId}`];
          break;

        case 'module_start':
          if (data.module) { modules[data.module] = 'running'; modules = { ...modules }; }
          logLines = [...logLines, `  [${data.module}] ${data.name} …`];
          break;

        case 'module_done':
          if (data.module) { modules[data.module] = 'done'; modules = { ...modules }; }
          completedModules++;
          if ((data.findings_count ?? 0) > 0) {
            liveFindings = [...liveFindings, { module: data.module ?? '', name: data.name ?? '', count: data.findings_count ?? 0 }];
            totalLiveFindings += data.findings_count ?? 0;
          }
          logLines = [...logLines, `  ✓ [${data.module}] ${data.name} — ${data.duration}s — ${data.findings_count ?? 0} findings`];
          break;

        case 'module_error':
          if (data.module) { modules[data.module] = 'error'; modules = { ...modules }; }
          completedModules++;
          logLines = [...logLines, `  ✗ [${data.module}] ${data.name} — FOUT: ${data.error}`];
          break;

        case 'log':
          logLines = [...logLines, `  · ${(data as any).message}`];
          break;

        case 'analysis_start':
          analysisStarted = true;
          logLines = [...logLines, '→ AI analyse bezig...'];
          break;

        case 'analysis_done':
          analysisStarted = false;
          logLines = [...logLines, '→ AI analyse voltooid'];
          break;

        case 'pdf_ready':
          logLines = [...logLines, '→ PDF gegenereerd'];
          break;

        case 'redirect':
          eventSource?.close();
          dispatch('navigate', (data as any).url || `/scan/${scanId}/report`);
          break;

        case 'all_done':
        case 'scan_complete':
          done = true;
          clearInterval(timer);
          logLines = [...logLines, `► Scan klaar in ${elapsed} — rapport openen...`];
          eventSource?.close();
          setTimeout(() => dispatch('navigate', `/scan/${scanId}/report`), 1000);
          break;

        case 'scan_stopped':
          done = true;
          clearInterval(timer);
          logLines = [...logLines, '■ Scan gestopt'];
          eventSource?.close();
          break;

        case 'error':
          logLines = [...logLines, `✗ FOUT: ${data.message}`];
          break;
      }
    };

    eventSource.onerror = () => {
      if (!done) logLines = [...logLines, '! Verbinding verloren — server herstart?'];
      eventSource?.close();
    };
  });

  onDestroy(() => {
    clearInterval(timer);
    eventSource?.close();
  });

  // Auto-scroll terminal
  afterUpdate(() => {
    if (terminalEl) terminalEl.scrollTop = terminalEl.scrollHeight;
  });

  async function handleStop() {
    stopping = true;
    try { await stopScan(scanId); } catch {}
    stopping = false;
  }

  $: progress = totalModules > 0 ? Math.round((completedModules / totalModules) * 100) : 0;

  function moduleIcon(status: string): string {
    return { done: '✓', running: '►', error: '✗', queued: '·' }[status] ?? '·';
  }
</script>

<div class="page-header">
  <h1 class="page-title">Scan — {scanId.slice(0, 15)}</h1>
  <div style="display: flex; gap: var(--space-2); align-items: center;">
    <span style="font-size: 11px; color: var(--text-3); font-variant-numeric: tabular-nums;">{elapsed}</span>
    {#if !done}
      <button class="btn btn-danger" on:click={handleStop} disabled={stopping}>
        {stopping ? '…' : '■ Stop'}
      </button>
    {:else}
      <button class="btn" on:click={() => dispatch('navigate', `/scan/${scanId}/report`)}>
        Rapport →
      </button>
    {/if}
  </div>
</div>

<!-- Progress bar -->
<div style="margin-bottom: var(--space-4);">
  <div style="display: flex; justify-content: space-between; margin-bottom: var(--space-1);">
    <span style="font-size: 11px; color: var(--text-2);">
      {#if analysisStarted}AI analyse…{:else if done}Klaar{:else}Modules{/if}
    </span>
    <span style="font-size: 11px; color: var(--text-2);">{completedModules}/{totalModules} &nbsp; {progress}%</span>
  </div>
  <div class="progress-track">
    <div class="progress-fill" style="width: {progress}%; transition: width 0.5s;"></div>
  </div>
</div>

<!-- Stats row -->
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: var(--border); margin-bottom: var(--space-4);">
  {#each [
    { label: 'Modules klaar', value: completedModules + (totalModules ? ` / ${totalModules}` : '') },
    { label: 'Live findings', value: totalLiveFindings, color: totalLiveFindings > 0 ? 'var(--high)' : 'var(--text)' },
    { label: 'Modules met findings', value: liveFindings.length },
  ] as s}
    <div style="background: var(--bg-2); padding: var(--space-3);">
      <div style="font-size: 22px; font-weight: 700; color: {s.color ?? 'var(--text)'};">{s.value}</div>
      <div style="font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3);">{s.label}</div>
    </div>
  {/each}
</div>

<!-- Module grid -->
{#if Object.keys(modules).length > 0}
  <div class="card" style="margin-bottom: var(--space-4);">
    <div class="card-header">
      <span class="card-title">Modules ({Object.keys(modules).length})</span>
      <span class="card-title" style="color: var(--text-3);">
        ✓ {Object.values(modules).filter(v => v === 'done').length} &nbsp;
        ► {Object.values(modules).filter(v => v === 'running').length} &nbsp;
        ✗ {Object.values(modules).filter(v => v === 'error').length}
      </span>
    </div>
    <div class="modules-grid">
      {#each Object.entries(modules) as [id, status]}
        <div class="module-cell {status}" title="{id}">
          {moduleIcon(status)} {id}
        </div>
      {/each}
    </div>
  </div>
{/if}

<!-- Live findings table -->
{#if liveFindings.length > 0}
  <div class="card" style="margin-bottom: var(--space-4);">
    <div class="card-header">
      <span class="card-title">Modules met findings</span>
      <span class="card-title">{totalLiveFindings} totaal</span>
    </div>
    <table class="findings-table">
      <thead><tr><th>Module</th><th>Naam</th><th style="text-align:right;">Findings</th></tr></thead>
      <tbody>
        {#each liveFindings as lf}
          <tr>
            <td style="color: var(--text-3); font-size: 11px;">{lf.module}</td>
            <td>{lf.name}</td>
            <td style="text-align:right; font-weight: 700;">{lf.count}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<!-- Terminal -->
<div class="card">
  <div class="card-header">
    <span class="card-title">Log</span>
    <span class="card-title" style="color: var(--text-3);">{logLines.length} regels</span>
  </div>
  <div class="terminal" bind:this={terminalEl} style="max-height: 340px;">
    {#each logLines as line}
      <div class={
        line.startsWith('✗') || line.includes('FOUT') ? 'log-error' :
        line.startsWith('►') ? 'log-module' :
        line.startsWith('→') ? 'log-info' :
        line.startsWith('  ✓') ? 'log-done' :
        'log-info'
      }>{line}</div>
    {/each}
    {#if analysisStarted && !done}
      <div class="log-info blink">→ AI analyse bezig...</div>
    {/if}
  </div>
</div>

<style>
  .blink { animation: blink 1.5s infinite; }
  @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
</style>
