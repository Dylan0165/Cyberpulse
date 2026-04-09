<script lang="ts">
  import { onMount } from 'svelte';
  import { getSchedules, createSchedule, deleteSchedule, toggleSchedule } from '../lib/api';

  let schedules: any[] = [];
  let loading = true;
  let error = '';
  let showForm = false;

  // Form state
  let form = { target: '', scan_type: 'quick', scan_mode: 'blackbox', target_type: 'web', interval: 'weekly', enabled: true };
  let submitting = false;

  const INTERVALS = [
    { value: 'daily', label: 'Dagelijks' },
    { value: 'weekly', label: 'Wekelijks' },
    { value: 'monthly', label: 'Maandelijks' },
  ];

  onMount(async () => {
    await reload();
    loading = false;
  });

  async function reload() {
    try {
      schedules = await getSchedules();
    } catch (e: any) {
      error = e.message;
    }
  }

  async function submit() {
    if (!form.target.trim()) return;
    submitting = true;
    try {
      await createSchedule({ ...form });
      showForm = false;
      form = { target: '', scan_type: 'quick', scan_mode: 'blackbox', target_type: 'web', interval: 'weekly', enabled: true };
      await reload();
    } catch (e: any) {
      error = e.message;
    } finally {
      submitting = false;
    }
  }

  async function remove(id: string) {
    await deleteSchedule(id);
    await reload();
  }

  async function toggle(id: string, enabled: boolean) {
    await toggleSchedule(id, !enabled);
    await reload();
  }

  function formatDate(ts: string | null): string {
    if (!ts) return '—';
    try { return new Date(ts).toLocaleString('nl-NL', { dateStyle: 'short', timeStyle: 'short' }); } catch { return ts; }
  }
</script>

<div class="schedule-page">
  <header class="page-header">
    <div>
      <h1>Geplande Scans</h1>
      <p class="subtitle">{schedules.length} gepland</p>
    </div>
    <button class="btn-primary" on:click={() => showForm = !showForm}>
      {showForm ? '✕ Annuleer' : '+ Nieuwe planning'}
    </button>
  </header>

  {#if showForm}
    <div class="form-card">
      <h2>Nieuwe scan plannen</h2>
      <div class="form-grid">
        <label>
          <span>Target *</span>
          <input bind:value={form.target} placeholder="example.com / 192.168.1.0/24" />
        </label>
        <label>
          <span>Interval</span>
          <select bind:value={form.interval}>
            {#each INTERVALS as iv}
              <option value={iv.value}>{iv.label}</option>
            {/each}
          </select>
        </label>
        <label>
          <span>Scan type</span>
          <select bind:value={form.scan_type}>
            <option value="quick">Quick</option>
            <option value="full">Full</option>
            <option value="custom">Custom</option>
          </select>
        </label>
        <label>
          <span>Modus</span>
          <select bind:value={form.scan_mode}>
            <option value="blackbox">Blackbox</option>
            <option value="greybox">Greybox</option>
            <option value="whitebox">Whitebox</option>
          </select>
        </label>
        <label>
          <span>Target type</span>
          <select bind:value={form.target_type}>
            <option value="web">Web</option>
            <option value="network">Netwerk</option>
            <option value="api">API</option>
          </select>
        </label>
      </div>
      <div class="form-actions">
        <button class="btn-primary" on:click={submit} disabled={submitting || !form.target.trim()}>
          {submitting ? 'Plannen…' : 'Planning aanmaken'}
        </button>
      </div>
    </div>
  {/if}

  {#if error}
    <div class="error-msg">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Laden…</div>
  {:else if schedules.length === 0}
    <div class="empty-state">
      <p>Geen geplande scans. Maak een planning aan om automatisch te scannen.</p>
    </div>
  {:else}
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Target</th>
            <th>Interval</th>
            <th>Type / Modus</th>
            <th>Volgende scan</th>
            <th>Laatste scan</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each schedules as s (s.id)}
            <tr class:disabled={!s.enabled}>
              <td class="mono">{s.target}</td>
              <td><span class="interval-badge">{s.interval}</span></td>
              <td>{s.scan_type} / {s.scan_mode}</td>
              <td class="muted">{formatDate(s.next_run)}</td>
              <td class="muted">{s.last_run ? formatDate(s.last_run) : '—'}</td>
              <td>
                <button class="toggle-btn {s.enabled ? 'active' : ''}" on:click={() => toggle(s.id, s.enabled)}>
                  {s.enabled ? 'Actief' : 'Inactief'}
                </button>
              </td>
              <td>
                <button class="icon-btn danger" on:click={() => remove(s.id)} title="Verwijderen">✕</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .schedule-page { padding: 2rem; max-width: 1100px; }
  .page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .subtitle { color: var(--text-muted, #888); font-size: 0.85rem; margin: 0.25rem 0 0; }
  .btn-primary { background: var(--accent, #1a1a1a); border: 1px solid var(--border, #444);
                 color: var(--text, #fff); padding: 0.5rem 1.25rem; cursor: pointer; font-size: 0.875rem; }
  .btn-primary:hover:not(:disabled) { border-color: var(--highlight, #0ff); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .form-card { background: var(--surface, #111); border: 1px solid var(--border, #333);
               padding: 1.5rem; margin-bottom: 1.5rem; }
  .form-card h2 { font-size: 1rem; font-weight: 600; margin: 0 0 1rem; }
  .form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
  .form-grid label { display: flex; flex-direction: column; gap: 0.375rem; font-size: 0.8rem;
                     color: var(--text-muted, #888); }
  .form-grid input, .form-grid select {
    background: var(--bg, #0e0e0e); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.4rem 0.75rem; font-size: 0.875rem; outline: none;
  }
  .form-grid input:focus, .form-grid select:focus { border-color: var(--highlight, #0ff); }
  .form-actions { margin-top: 1rem; }
  .table-wrapper { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
  th { text-align: left; padding: 0.75rem 1rem; background: var(--surface, #1a1a1a);
       border-bottom: 2px solid var(--border, #333); color: var(--text-muted, #888);
       font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }
  td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border, #222); vertical-align: middle; }
  tr.disabled td { opacity: 0.5; }
  .mono { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
  .muted { color: var(--text-muted, #888); font-size: 0.8rem; }
  .interval-badge { background: var(--surface, #222); border: 1px solid var(--border, #333);
                    padding: 0.15rem 0.5rem; font-size: 0.75rem; }
  .toggle-btn { padding: 0.2rem 0.6rem; font-size: 0.75rem; cursor: pointer; border: 1px solid var(--border, #444);
                background: transparent; color: var(--text-muted, #888); }
  .toggle-btn.active { border-color: #00cc66; color: #00cc66; }
  .icon-btn { background: none; border: none; cursor: pointer; color: var(--text-muted, #888); font-size: 1rem; padding: 0.25rem; }
  .icon-btn.danger:hover { color: #ff4444; }
  .loading, .empty-state { color: var(--text-muted, #888); padding: 3rem; text-align: center; }
  .error-msg { color: #ff4444; padding: 0.75rem; border: 1px solid #ff4444; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
