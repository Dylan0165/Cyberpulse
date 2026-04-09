<script lang="ts">
  import { onMount } from 'svelte';
  import { getNotifications, markNotificationRead, markAllRead, clearNotifications, getUnreadCount } from '../lib/api';

  let notifications: any[] = [];
  let loading = true;
  let error = '';
  let unreadCount = 0;

  onMount(() => reload());

  async function reload() {
    loading = true;
    try {
      [notifications, { count: unreadCount }] = await Promise.all([
        getNotifications(50),
        getUnreadCount(),
      ]);
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function markRead(id: string) {
    await markNotificationRead(id);
    await reload();
  }

  async function readAll() {
    await markAllRead();
    await reload();
  }

  async function clearAll() {
    if (!confirm('Alle meldingen verwijderen?')) return;
    await clearNotifications();
    await reload();
  }

  function formatTs(ts: string): string {
    try {
      const d = new Date(ts);
      const now = new Date();
      const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000);
      if (diffMin < 1) return 'Zojuist';
      if (diffMin < 60) return `${diffMin} min geleden`;
      if (diffMin < 1440) return `${Math.floor(diffMin / 60)} uur geleden`;
      return d.toLocaleDateString('nl-NL');
    } catch { return ts; }
  }

  const SEV_ICONS: Record<string, string> = {
    critical: '🔴', high: '🟠', medium: '🟡', low: '🟢', info: '🔵',
  };
</script>

<div class="notif-page">
  <header class="page-header">
    <div>
      <h1>Meldingen</h1>
      {#if unreadCount > 0}
        <span class="badge">{unreadCount} ongelezen</span>
      {/if}
    </div>
    <div class="header-actions">
      {#if unreadCount > 0}
        <button class="btn-secondary" on:click={readAll}>Alles als gelezen markeren</button>
      {/if}
      {#if notifications.length > 0}
        <button class="btn-danger" on:click={clearAll}>Wis alles</button>
      {/if}
    </div>
  </header>

  {#if error}
    <div class="error-msg">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Laden…</div>
  {:else if notifications.length === 0}
    <div class="empty-state">
      <p>Geen meldingen. Meldingen verschijnen hier na een volgende scan.</p>
    </div>
  {:else}
    <div class="notif-list">
      {#each notifications as n (n.id)}
        <div class="notif-item" class:unread={!n.read} on:click={() => !n.read && markRead(n.id)} role="button" tabindex="0" on:keydown={e => e.key === 'Enter' && !n.read && markRead(n.id)}>
          <div class="notif-icon">{SEV_ICONS[n.severity] ?? '●'}</div>
          <div class="notif-body">
            <div class="notif-title">{n.title}</div>
            <div class="notif-msg">{n.message}</div>
            {#if n.scan_id}
              <div class="notif-meta">Scan: <span class="mono">{n.scan_id?.slice(0, 12)}</span></div>
            {/if}
          </div>
          <div class="notif-ts">{formatTs(n.created_at)}</div>
          {#if !n.read}
            <div class="unread-dot"></div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .notif-page { padding: 2rem; max-width: 800px; }
  .page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 1.5rem; }
  .page-header h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
  .badge { display: inline-block; background: #ff4444; color: #fff; padding: 0.15rem 0.6rem;
           font-size: 0.75rem; font-weight: 700; margin-left: 0.5rem; vertical-align: middle; }
  .header-actions { display: flex; gap: 0.5rem; }
  .btn-secondary { background: none; border: 1px solid var(--border, #444); color: var(--text-muted, #aaa);
                   padding: 0.4rem 1rem; cursor: pointer; font-size: 0.875rem; }
  .btn-secondary:hover { border-color: var(--highlight, #0ff); color: var(--text, #fff); }
  .btn-danger { background: none; border: 1px solid #ff4444; color: #ff4444;
                padding: 0.4rem 1rem; cursor: pointer; font-size: 0.875rem; }
  .btn-danger:hover { background: rgba(255,68,68,.1); }
  .notif-list { display: flex; flex-direction: column; gap: 0; }
  .notif-item {
    display: flex; align-items: flex-start; gap: 0.75rem;
    padding: 1rem; border-bottom: 1px solid var(--border, #222);
    cursor: pointer; position: relative; transition: background 0.1s;
  }
  .notif-item:hover { background: var(--surface, #111); }
  .notif-item.unread { background: var(--surface, #0f0f1a); }
  .notif-icon { font-size: 1.2rem; flex-shrink: 0; padding-top: 0.1rem; }
  .notif-body { flex: 1; min-width: 0; }
  .notif-title { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.2rem; }
  .notif-msg { font-size: 0.825rem; color: var(--text-muted, #aaa); line-height: 1.5; }
  .notif-meta { font-size: 0.75rem; color: var(--text-muted, #666); margin-top: 0.25rem; }
  .mono { font-family: monospace; }
  .notif-ts { font-size: 0.75rem; color: var(--text-muted, #666); flex-shrink: 0; white-space: nowrap; padding-top: 0.1rem; }
  .unread-dot { position: absolute; left: 0.4rem; top: 50%; transform: translateY(-50%);
                width: 6px; height: 6px; background: var(--highlight, #0ff); border-radius: 50%; }
  .loading, .empty-state { color: var(--text-muted, #888); text-align: center; padding: 3rem; }
  .error-msg { color: #ff4444; padding: 0.75rem; border: 1px solid #ff4444; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
