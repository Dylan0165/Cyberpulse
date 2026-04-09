<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getWebhooks, createWebhook, deleteWebhook,
    getApiKeys, createApiKey, deleteApiKey
  } from '../lib/api';

  let tab: 'webhooks' | 'apikeys' = 'webhooks';
  let webhooks: any[] = [];
  let apiKeys: any[] = [];
  let loadingW = true;
  let loadingK = true;
  let error = '';

  // Webhook form
  let wUrl = '';
  let wEvents: string[] = ['scan_completed'];
  let addingW = false;

  // API key form
  let kName = '';
  let kScope = 'read';
  let addingK = false;
  let newKeyVal = '';

  const AVAILABLE_EVENTS = [
    'scan_completed', 'scan_failed', 'critical_finding', 'high_finding', 'scan_started',
  ];

  onMount(async () => {
    await Promise.all([loadWebhooks(), loadKeys()]);
  });

  async function loadWebhooks() {
    loadingW = true;
    try { webhooks = await getWebhooks(); } catch (e: any) { error = e.message; } finally { loadingW = false; }
  }

  async function loadKeys() {
    loadingK = true;
    try { apiKeys = await getApiKeys(); } catch (e: any) { error = e.message; } finally { loadingK = false; }
  }

  async function addWebhook() {
    if (!wUrl.trim()) return;
    addingW = true;
    try {
      await createWebhook({ url: wUrl.trim(), events: wEvents });
      wUrl = '';
      await loadWebhooks();
    } catch (e: any) {
      error = e.message;
    } finally {
      addingW = false;
    }
  }

  async function removeWebhook(id: string) {
    await deleteWebhook(id);
    await loadWebhooks();
  }

  async function addKey() {
    if (!kName.trim()) return;
    addingK = true;
    try {
      const result = await createApiKey({ name: kName.trim(), scope: kScope });
      newKeyVal = result.key;
      kName = '';
      await loadKeys();
    } catch (e: any) {
      error = e.message;
    } finally {
      addingK = false;
    }
  }

  async function removeKey(id: string) {
    await deleteApiKey(id);
    await loadKeys();
  }

  function toggleEvent(e: string) {
    if (wEvents.includes(e)) {
      wEvents = wEvents.filter(x => x !== e);
    } else {
      wEvents = [...wEvents, e];
    }
  }
</script>

<div class="integrations-page">
  <header class="page-header">
    <h1>Integraties &amp; API</h1>
    <p class="subtitle">Webhooks, API keys en externe koppelingen</p>
  </header>

  <div class="tabs">
    <button class="tab-btn" class:active={tab === 'webhooks'} on:click={() => tab = 'webhooks'}>Webhooks</button>
    <button class="tab-btn" class:active={tab === 'apikeys'} on:click={() => tab = 'apikeys'}>API Keys</button>
  </div>

  {#if error}
    <div class="error-msg">{error} <button on:click={() => error = ''}>✕</button></div>
  {/if}

  {#if tab === 'webhooks'}
    <section class="section">
      <h2>Webhook aanmaken</h2>
      <div class="form-row">
        <input bind:value={wUrl} placeholder="https://hooks.example.com/..." class="url-input" />
        <div class="event-checkboxes">
          {#each AVAILABLE_EVENTS as ev}
            <label class="checkbox-label">
              <input type="checkbox" checked={wEvents.includes(ev)} on:change={() => toggleEvent(ev)} />
              {ev}
            </label>
          {/each}
        </div>
        <button class="btn-primary" on:click={addWebhook} disabled={addingW || !wUrl.trim()}>
          {addingW ? 'Aanmaken…' : '+ Toevoegen'}
        </button>
      </div>

      <div class="list">
        {#if loadingW}
          <div class="loading">Laden…</div>
        {:else if webhooks.length === 0}
          <div class="empty">Geen webhooks geconfigureerd.</div>
        {:else}
          {#each webhooks as wh (wh.id)}
            <div class="list-row">
              <span class="mono url">{wh.url}</span>
              <div class="events">
                {#each (wh.events ?? []) as ev}
                  <span class="event-tag">{ev}</span>
                {/each}
              </div>
              <span class="status {wh.enabled ? 'active' : 'inactive'}">{wh.enabled ? 'Actief' : 'Inactief'}</span>
              <button class="icon-btn danger" on:click={() => removeWebhook(wh.id)}>✕</button>
            </div>
          {/each}
        {/if}
      </div>
    </section>
  {:else}
    <section class="section">
      <h2>API Key aanmaken</h2>
      <div class="form-row compact">
        <input bind:value={kName} placeholder="Naam (bijv. CI/CD pipeline)" class="name-input" />
        <select bind:value={kScope}>
          <option value="read">Read-only</option>
          <option value="scan">Scan</option>
          <option value="admin">Admin</option>
        </select>
        <button class="btn-primary" on:click={addKey} disabled={addingK || !kName.trim()}>
          {addingK ? 'Aanmaken…' : '+ Aanmaken'}
        </button>
      </div>

      {#if newKeyVal}
        <div class="key-reveal">
          <span class="label">Nieuwe API key (eenmalig zichtbaar):</span>
          <span class="key-val mono">{newKeyVal}</span>
          <button on:click={() => { navigator.clipboard.writeText(newKeyVal); }}>Kopieer</button>
        </div>
      {/if}

      <div class="list">
        {#if loadingK}
          <div class="loading">Laden…</div>
        {:else if apiKeys.length === 0}
          <div class="empty">Geen API keys aangemaakt.</div>
        {:else}
          {#each apiKeys as k (k.id)}
            <div class="list-row">
              <span class="key-name">{k.name}</span>
              <span class="mono muted">{k.key}</span>
              <span class="scope-tag">{k.scope}</span>
              <span class="muted date">{k.last_used ? `Gebruikt: ${new Date(k.last_used).toLocaleDateString('nl-NL')}` : 'Nog niet gebruikt'}</span>
              <button class="icon-btn danger" on:click={() => removeKey(k.id)}>✕</button>
            </div>
          {/each}
        {/if}
      </div>
    </section>
  {/if}
</div>

<style>
  .integrations-page { padding: 2rem; max-width: 900px; }
  .page-header { margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .subtitle { color: var(--text-muted, #888); font-size: 0.85rem; margin: 0.25rem 0 0; }
  .tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border, #333); margin-bottom: 1.5rem; }
  .tab-btn {
    background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-muted, #888); padding: 0.6rem 1.25rem; cursor: pointer; font-size: 0.875rem;
    margin-bottom: -1px;
  }
  .tab-btn.active { color: var(--text, #fff); border-bottom-color: var(--highlight, #0ff); }
  .section h2 { font-size: 1rem; font-weight: 600; margin: 0 0 1rem; }
  .form-row { display: flex; align-items: flex-start; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
  .form-row.compact { align-items: center; }
  .url-input, .name-input {
    background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.4rem 0.75rem; font-size: 0.875rem; flex: 1; min-width: 260px;
  }
  .name-input { max-width: 240px; }
  select {
    background: var(--surface, #111); border: 1px solid var(--border, #333);
    color: var(--text, #fff); padding: 0.4rem 0.75rem; font-size: 0.875rem;
  }
  .event-checkboxes { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
  .checkbox-label { display: flex; align-items: center; gap: 0.3rem; font-size: 0.8rem;
                    color: var(--text-muted, #aaa); cursor: pointer; }
  .btn-primary { background: var(--surface, #1a1a1a); border: 1px solid var(--border, #444);
                 color: var(--text, #fff); padding: 0.4rem 1rem; cursor: pointer; font-size: 0.875rem; }
  .btn-primary:hover:not(:disabled) { border-color: var(--highlight, #0ff); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .list { display: flex; flex-direction: column; gap: 0.5rem; }
  .list-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem;
              background: var(--surface, #111); border: 1px solid var(--border, #222); flex-wrap: wrap; }
  .mono { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
  .url { color: var(--highlight, #0ff); flex: 1; }
  .events { display: flex; flex-wrap: wrap; gap: 0.25rem; }
  .event-tag { background: var(--surface, #222); border: 1px solid var(--border, #333);
               padding: 0.1rem 0.4rem; font-size: 0.7rem; }
  .status.active { color: #00cc66; }
  .status.inactive { color: #888; }
  .scope-tag { background: rgba(100,149,237,.15); color: #6495ed; border: 1px solid #6495ed;
               padding: 0.15rem 0.5rem; font-size: 0.75rem; }
  .key-name { font-weight: 600; min-width: 120px; }
  .muted { color: var(--text-muted, #888); }
  .date { font-size: 0.75rem; }
  .icon-btn { background: none; border: none; cursor: pointer; color: var(--text-muted, #666); font-size: 1rem; padding: 0.2rem 0.4rem; }
  .icon-btn.danger:hover { color: #ff4444; }
  .key-reveal { background: rgba(0,200,0,.05); border: 1px solid #00cc66;
                padding: 0.75rem 1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
  .key-reveal .label { font-size: 0.8rem; color: var(--text-muted, #888); }
  .key-val { color: #00cc66; flex: 1; word-break: break-all; }
  .key-reveal button { background: none; border: 1px solid #00cc66; color: #00cc66;
                       padding: 0.2rem 0.6rem; cursor: pointer; font-size: 0.8rem; }
  .loading, .empty { color: var(--text-muted, #888); text-align: center; padding: 2rem; }
  .error-msg { color: #ff4444; padding: 0.5rem 0.75rem; border: 1px solid #ff4444;
               margin-bottom: 1rem; display: flex; justify-content: space-between; font-size: 0.875rem; }
  .error-msg button { background: none; border: none; color: #ff4444; cursor: pointer; }
</style>
