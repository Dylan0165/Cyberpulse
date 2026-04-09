<script lang="ts">
  import { onMount } from 'svelte';
  import { engineStatus, currentRoute } from './lib/stores';
  import { healthCheck, getUnreadCount } from './lib/api';
  import Dashboard from './routes/Dashboard.svelte';
  import NewScan from './routes/NewScan.svelte';
  import ScanProgress from './routes/ScanProgress.svelte';
  import Report from './routes/Report.svelte';
  import Settings from './routes/Settings.svelte';
  import Tools from './routes/Tools.svelte';
  import Assets from './routes/Assets.svelte';
  import Schedule from './routes/Schedule.svelte';
  import Chat from './routes/Chat.svelte';
  import Compliance from './routes/Compliance.svelte';
  import Compare from './routes/Compare.svelte';
  import Integrations from './routes/Integrations.svelte';
  import AuditLog from './routes/AuditLog.svelte';
  import Notifications from './routes/Notifications.svelte';

  let route = '/';
  let routeParam = '';
  let unreadNotifications = 0;

  currentRoute.subscribe(v => {
    if (v.startsWith('/scan/') && v.endsWith('/progress')) {
      route = '/scan/progress';
      routeParam = v.split('/')[2];
    } else if (v.startsWith('/scan/') && v.endsWith('/report')) {
      route = '/scan/report';
      routeParam = v.split('/')[2];
    } else if (v.startsWith('/chat/')) {
      route = '/chat';
      routeParam = v.split('/')[2] || '';
    } else {
      route = v;
      routeParam = '';
    }
  });

  function navigate(path: string) {
    currentRoute.set(path);
  }

  onMount(async () => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === 'n' || e.key === 'N') navigate('/scan/new');
      if (e.key === 'h' || e.key === 'H') navigate('/');
      if (e.key === 't' || e.key === 'T') navigate('/tools');
      if (e.key === 'Escape') navigate('/');
    };
    window.addEventListener('keydown', onKey);

    let attempts = 0;
    const maxAttempts = 20;
    const poll = setInterval(async () => {
      const ok = await healthCheck();
      if (ok) {
        engineStatus.set('online');
        clearInterval(poll);
        // Poll unread notifications every 30s
        setInterval(async () => {
          try {
            const { count } = await getUnreadCount();
            unreadNotifications = count;
          } catch {}
        }, 30000);
        try {
          const { count } = await getUnreadCount();
          unreadNotifications = count;
        } catch {}
      } else {
        attempts++;
        if (attempts >= maxAttempts) {
          engineStatus.set('offline');
          clearInterval(poll);
        }
      }
    }, 500);
    return () => window.removeEventListener('keydown', onKey);
  });

  $: isActive = (path: string) => route === path ? 'nav-item active' : 'nav-item';
</script>

{#if $engineStatus === 'checking'}
  <div class="loading-screen">
    <h1>CyberPulse</h1>
    <p>Engine starten...</p>
    <div class="progress-track" style="width: 200px;">
      <div class="progress-fill" style="width: 60%; animation: pulse 1.5s infinite;"></div>
    </div>
  </div>
{:else if $engineStatus === 'offline'}
  <div class="loading-screen">
    <h1>CyberPulse</h1>
    <p style="color: var(--critical);">Engine niet bereikbaar</p>
    <button class="btn" on:click={() => { engineStatus.set('checking'); location.reload(); }}>
      Herstart
    </button>
  </div>
{:else}
  <div class="app-shell">
    <nav class="sidebar">
      <div class="sidebar-logo">
        Cyber<span>Pulse</span>
      </div>

      <div class="nav-section-label">Algemeen</div>
      <div class={isActive('/')} on:click={() => navigate('/')} on:keydown={() => navigate('/')} role="button" tabindex="0">
        ◆ Dashboard
      </div>
      <div class={isActive('/scan/new')} on:click={() => navigate('/scan/new')} on:keydown={() => navigate('/scan/new')} role="button" tabindex="0">
        + Nieuwe Scan
      </div>
      <div class={isActive('/assets')} on:click={() => navigate('/assets')} on:keydown={() => navigate('/assets')} role="button" tabindex="0">
        🖥 Assets
      </div>
      <div class={isActive('/schedule')} on:click={() => navigate('/schedule')} on:keydown={() => navigate('/schedule')} role="button" tabindex="0">
        📅 Planning
      </div>

      <div class="nav-section-label">Analyse</div>
      <div class={isActive('/chat')} on:click={() => navigate('/chat')} on:keydown={() => navigate('/chat')} role="button" tabindex="0">
        💬 AI Chat
      </div>
      <div class={isActive('/compliance')} on:click={() => navigate('/compliance')} on:keydown={() => navigate('/compliance')} role="button" tabindex="0">
        🛡 Compliance
      </div>
      <div class={isActive('/compare')} on:click={() => navigate('/compare')} on:keydown={() => navigate('/compare')} role="button" tabindex="0">
        ⚖ Vergelijken
      </div>

      <div class="nav-section-label">Beheer</div>
      <div class={isActive('/tools')} on:click={() => navigate('/tools')} on:keydown={() => navigate('/tools')} role="button" tabindex="0">
        ⚒ Tools
      </div>
      <div class={isActive('/integrations')} on:click={() => navigate('/integrations')} on:keydown={() => navigate('/integrations')} role="button" tabindex="0">
        🔗 Integraties
      </div>
      <div class={isActive('/notifications')} on:click={() => navigate('/notifications')} on:keydown={() => navigate('/notifications')} role="button" tabindex="0">
        🔔 Meldingen{#if unreadNotifications > 0}<span class="notif-badge">{unreadNotifications}</span>{/if}
      </div>
      <div class={isActive('/audit')} on:click={() => navigate('/audit')} on:keydown={() => navigate('/audit')} role="button" tabindex="0">
        📋 Audit Log
      </div>
      <div class={isActive('/settings')} on:click={() => navigate('/settings')} on:keydown={() => navigate('/settings')} role="button" tabindex="0">
        ⚙ Instellingen
      </div>

      <div style="flex: 1;"></div>
      <div style="padding: var(--space-2) var(--space-4); font-size: 10px; color: var(--text-3); line-height: 1.8;">
        <span class="status-dot online"></span> Engine online<br>
        <span style="opacity: 0.5;">N scan · T tools · H home · Esc terug</span>
      </div>
    </nav>

    <main class="main">
      {#if route === '/'}
        <Dashboard on:navigate={(e) => navigate(e.detail)} />
      {:else if route === '/scan/new'}
        <NewScan on:navigate={(e) => navigate(e.detail)} />
      {:else if route === '/scan/progress'}
        <ScanProgress scanId={routeParam} on:navigate={(e) => navigate(e.detail)} />
      {:else if route === '/scan/report'}
        <Report scanId={routeParam} on:navigate={(e) => navigate(e.detail)} />
      {:else if route === '/tools'}
        <Tools on:navigate={(e) => navigate(e.detail)} />
      {:else if route === '/assets'}
        <Assets />
      {:else if route === '/schedule'}
        <Schedule />
      {:else if route === '/chat'}
        <Chat scanId={routeParam} />
      {:else if route === '/compliance'}
        <Compliance />
      {:else if route === '/compare'}
        <Compare />
      {:else if route === '/integrations'}
        <Integrations />
      {:else if route === '/notifications'}
        <Notifications />
      {:else if route === '/audit'}
        <AuditLog />
      {:else if route === '/settings'}
        <Settings />
      {:else}
        <Dashboard on:navigate={(e) => navigate(e.detail)} />
      {/if}
    </main>
  </div>
{/if}

<style>
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .nav-section-label {
    padding: 0.8rem var(--space-4, 1rem) 0.25rem;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-3, #555);
    margin-top: 0.25rem;
  }
  .notif-badge {
    display: inline-block;
    background: #ff4444;
    color: #fff;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0 0.35rem;
    margin-left: 0.4rem;
    vertical-align: middle;
    min-width: 1rem;
    text-align: center;
  }
</style>

