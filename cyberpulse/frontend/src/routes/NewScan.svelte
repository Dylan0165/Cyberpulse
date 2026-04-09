<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { startScan, getAvailableTools } from '../lib/api';

  const dispatch = createEventDispatcher();

  // ── Target state
  let target = '';
  let targetType = 'web';

  // ── Scan config
  let scanType = 'standard';
  let scanMode = 'blackbox';
  let submitting = false;
  let error = '';

  // ── Credentials (graybox / whitebox)
  let credUsername = '';
  let credPassword = '';
  let credLoginUrl = '';
  let credApiToken = '';
  let credSshHost = '';
  let credSshUser = '';
  let credSshPass = '';

  // ── Tool selection (custom mode)
  let toolsData: any = null;
  let toolsLoading = false;
  let toolSearch = '';
  let activeCategory = 'all';
  let selectedTools: Set<string> = new Set();

  const targetTypes = [
    { value: 'web', label: 'Website / Webapp', icon: '🌐' },
    { value: 'api', label: 'REST API', icon: '⚡' },
    { value: 'spa', label: 'Dashboard / SPA', icon: '📱' },
    { value: 'mobile_ios', label: 'iOS (.ipa)', icon: '🍎' },
    { value: 'mobile_android', label: 'Android (.apk)', icon: '🤖' },
    { value: 'desktop', label: 'Desktop app', icon: '🖥' },
    { value: 'network', label: 'Netwerk / IP range', icon: '🔌' },
  ];

  const scanModes = [
    {
      value: 'blackbox',
      label: 'Blackbox',
      icon: '■',
      desc: 'Geen inloggegevens of interne kennis — test als externe aanvaller',
    },
    {
      value: 'graybox',
      label: 'Graybox',
      icon: '◧',
      desc: 'Met inloggegevens — test wat een geauthenticeerde gebruiker kan bereiken',
    },
    {
      value: 'whitebox',
      label: 'Whitebox',
      icon: '□',
      desc: 'Volledige toegang — inclusief broncode, servers en SSH',
    },
  ];

  const scanProfiles = [
    { value: 'quick', label: 'Snel', modules: 8, desc: 'Snelle check op de belangrijkste kwetsbaarheden' },
    { value: 'standard', label: 'Standaard', modules: 50, desc: 'Uitgebreide scan met de meest gebruikte tools' },
    { value: 'full', label: 'Volledig', modules: 100, desc: 'Alle beschikbare tools en modules worden ingezet' },
    { value: 'custom', label: 'Aangepast', modules: null, desc: 'Kies zelf welke tools je wilt inzetten' },
  ];

  const CATEGORY_LABELS: Record<string, string> = {
    all:               'Alles',
    password:          'Wachtwoorden',
    network_scanning:  'Netwerk',
    web:               'Web',
    wireless:          'Draadloos',
    sniffing:          'Sniffing',
    osint:             'OSINT',
    exploitation:      'Exploitation',
    post_exploit:      'Post-exploit',
    forensics:         'Forensics',
    reversing:         'Reversing',
    vuln_analysis:     'Kwetsbaarheidsanalyse',
    crypto:            'Crypto',
  };

  const CATEGORY_ICONS: Record<string, string> = {
    password:          '🔑',
    network_scanning:  '🌐',
    web:               '🕸',
    wireless:          '📡',
    sniffing:          '👃',
    osint:             '🔍',
    exploitation:      '💥',
    post_exploit:      '🏴',
    forensics:         '🔬',
    reversing:         '⚙',
    vuln_analysis:     '🛡',
    crypto:            '🔐',
  };

  // ── Tool data
  $: allTools = toolsData
    ? Object.values(toolsData as Record<string, any>)
    : [];

  $: categories = allTools.length
    ? ['all', ...[...new Set(allTools.map((t: any) => t.category).filter(Boolean))].sort()]
    : ['all'];

  $: filteredTools = allTools.filter((t: any) => {
    const matchCat = activeCategory === 'all' || t.category === activeCategory;
    const matchSearch = !toolSearch ||
      t.name?.toLowerCase().includes(toolSearch.toLowerCase()) ||
      t.display_name?.toLowerCase().includes(toolSearch.toLowerCase());
    return matchCat && matchSearch;
  });

  // Load tools when switching to custom
  $: if (scanType === 'custom' && !toolsData && !toolsLoading) {
    loadTools();
  }

  async function loadTools() {
    toolsLoading = true;
    try {
      toolsData = await getAvailableTools();
    } catch { /* ignore */ }
    toolsLoading = false;
  }

  function toggleTool(name: string) {
    if (selectedTools.has(name)) {
      selectedTools.delete(name);
    } else {
      selectedTools.add(name);
    }
    selectedTools = selectedTools; // trigger reactivity
  }

  function selectAllFiltered() {
    for (const t of filteredTools) {
      selectedTools.add(t.name);
    }
    selectedTools = selectedTools;
  }

  function deselectAllFiltered() {
    for (const t of filteredTools) {
      selectedTools.delete(t.name);
    }
    selectedTools = selectedTools;
  }

  async function handleSubmit() {
    if (!target.trim()) {
      error = 'Vul een target in';
      return;
    }
    if (scanType === 'custom' && selectedTools.size === 0) {
      error = 'Selecteer minimaal één tool';
      return;
    }
    error = '';
    submitting = true;

    const credentials: Record<string, string> = {};
    if (scanMode !== 'blackbox') {
      if (credUsername) credentials.web_username = credUsername;
      if (credPassword) credentials.web_password = credPassword;
      if (credLoginUrl) credentials.web_login_url = credLoginUrl;
      if (credApiToken) credentials.api_token = credApiToken;
      if (credSshHost) credentials.ssh_host = credSshHost;
      if (credSshUser) credentials.ssh_username = credSshUser;
      if (credSshPass) credentials.ssh_password = credSshPass;
    }

    try {
      const result = await startScan({
        target: target.trim(),
        target_type: targetType,
        scan_type: scanType,
        scan_mode: scanMode,
        credentials: Object.keys(credentials).length > 0 ? credentials : undefined,
        modules: scanType === 'custom' ? [...selectedTools] : undefined,
      });
      dispatch('navigate', `/scan/${result.scan_id}/progress`);
    } catch (e: any) {
      error = e.message || 'Scan starten mislukt';
      submitting = false;
    }
  }
</script>

<div class="page-header">
  <h1 class="page-title">Nieuwe Scan</h1>
  <span class="page-meta">Configureer en start een pentest</span>
</div>

<form on:submit|preventDefault={handleSubmit}>

  <!-- ─── TARGET ─────────────────────────── -->
  <section class="scan-section">
    <div class="section-label">1 — Target</div>
    <input
      id="target"
      type="text"
      bind:value={target}
      placeholder="https://example.nl, 192.168.1.0/24, /pad/naar/app.apk"
      disabled={submitting}
    />
    <div class="chip-row">
      {#each targetTypes as tt}
        <button
          type="button"
          class="chip"
          class:active={targetType === tt.value}
          on:click={() => targetType = tt.value}
          disabled={submitting}
        >
          {tt.icon} {tt.label}
        </button>
      {/each}
    </div>
  </section>

  <!-- ─── MODUS ──────────────────────────── -->
  <section class="scan-section">
    <div class="section-label">2 — Modus</div>
    <div class="mode-grid">
      {#each scanModes as mode}
        <button
          type="button"
          class="mode-card"
          class:active={scanMode === mode.value}
          on:click={() => scanMode = mode.value}
          disabled={submitting}
        >
          <span class="mode-icon">{mode.icon}</span>
          <span class="mode-label">{mode.label}</span>
          <span class="mode-desc">{mode.desc}</span>
        </button>
      {/each}
    </div>
  </section>

  <!-- ─── CREDENTIALS (graybox / whitebox) ── -->
  {#if scanMode !== 'blackbox'}
    <section class="scan-section">
      <div class="section-label">
        {scanMode === 'graybox' ? '2a — Inloggegevens' : '2a — Toegangsgegevens'}
      </div>
      <div class="cred-grid">
        <div class="form-group">
          <label for="cred-user">Web gebruikersnaam</label>
          <input id="cred-user" type="text" bind:value={credUsername} />
        </div>
        <div class="form-group">
          <label for="cred-pass">Web wachtwoord</label>
          <input id="cred-pass" type="password" bind:value={credPassword} />
        </div>
        <div class="form-group">
          <label for="cred-login">Login URL</label>
          <input id="cred-login" type="text" bind:value={credLoginUrl} placeholder="https://example.nl/login" />
        </div>
        <div class="form-group">
          <label for="cred-api">API Token</label>
          <input id="cred-api" type="password" bind:value={credApiToken} />
        </div>
        {#if scanMode === 'whitebox'}
          <div class="form-group">
            <label for="cred-ssh-host">SSH Host</label>
            <input id="cred-ssh-host" type="text" bind:value={credSshHost} />
          </div>
          <div class="form-group">
            <label for="cred-ssh-user">SSH Gebruiker</label>
            <input id="cred-ssh-user" type="text" bind:value={credSshUser} />
          </div>
          <div class="form-group">
            <label for="cred-ssh-pass">SSH Wachtwoord</label>
            <input id="cred-ssh-pass" type="password" bind:value={credSshPass} />
          </div>
        {/if}
      </div>
    </section>
  {/if}

  <!-- ─── SCAN PROFIEL ───────────────────── -->
  <section class="scan-section">
    <div class="section-label">3 — Scan profiel</div>
    <div class="profile-grid">
      {#each scanProfiles as sp}
        <button
          type="button"
          class="profile-card"
          class:active={scanType === sp.value}
          on:click={() => scanType = sp.value}
          disabled={submitting}
        >
          <span class="profile-name">{sp.label}</span>
          {#if sp.modules}
            <span class="profile-count">{sp.modules} modules</span>
          {:else}
            <span class="profile-count">{selectedTools.size || '—'} geselecteerd</span>
          {/if}
          <span class="profile-desc">{sp.desc}</span>
        </button>
      {/each}
    </div>
  </section>

  <!-- ─── TOOL SELECTIE (custom) ─────────── -->
  {#if scanType === 'custom'}
    <section class="scan-section">
      <div class="section-label">
        4 — Tools selecteren
        <span class="section-meta">{selectedTools.size} geselecteerd</span>
      </div>

      {#if toolsLoading}
        <div style="color: var(--text-3); padding: var(--space-3);">Tools laden...</div>
      {:else}
        <div class="tool-controls">
          <input
            type="text"
            placeholder="Zoek tool..."
            bind:value={toolSearch}
            class="tool-search"
          />
          <button type="button" class="btn" on:click={selectAllFiltered}>Alles selecteren</button>
          <button type="button" class="btn" on:click={deselectAllFiltered}>Alles deselecteren</button>
        </div>

        <div class="cat-row">
          {#each categories as cat}
            <button
              type="button"
              class="cat-btn"
              class:active={activeCategory === cat}
              on:click={() => activeCategory = cat}
            >
              {CATEGORY_ICONS[cat] ?? ''} {CATEGORY_LABELS[cat] ?? cat}
            </button>
          {/each}
        </div>

        <div class="tool-select-grid">
          {#each filteredTools as tool}
            <button
              type="button"
              class="tool-item-select"
              class:selected={selectedTools.has(tool.name)}
              class:unavailable={!tool.available}
              on:click={() => toggleTool(tool.name)}
            >
              <span class="tool-check">{selectedTools.has(tool.name) ? '◼' : '◻'}</span>
              <span class="tool-info">
                <span class="tool-name">{tool.display_name || tool.name}</span>
                <span class="tool-cat-label">{CATEGORY_ICONS[tool.category] ?? ''} {CATEGORY_LABELS[tool.category] ?? tool.category}</span>
              </span>
              {#if !tool.available}
                <span class="tool-badge-na">n/a</span>
              {/if}
            </button>
          {/each}
        </div>
      {/if}
    </section>
  {/if}

  <!-- ─── SAMENVATTING & START ───────────── -->
  <section class="scan-section scan-footer">
    <div class="summary-row">
      <span class="summary-item">
        <strong>Target:</strong> {target || '—'}
      </span>
      <span class="summary-item">
        <strong>Type:</strong> {targetTypes.find(t => t.value === targetType)?.label ?? targetType}
      </span>
      <span class="summary-item">
        <strong>Modus:</strong> {scanModes.find(m => m.value === scanMode)?.label ?? scanMode}
      </span>
      <span class="summary-item">
        <strong>Profiel:</strong> {scanProfiles.find(s => s.value === scanType)?.label ?? scanType}
        {#if scanType === 'custom'}({selectedTools.size} tools){/if}
      </span>
    </div>

    {#if error}
      <p class="error-msg">{error}</p>
    {/if}

    <button class="btn btn-primary btn-start" type="submit" disabled={submitting}>
      {submitting ? 'Bezig met starten...' : '▶ Scan Starten'}
    </button>
  </section>

</form>

<style>
  form {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  /* ── Section blocks */
  .scan-section {
    background: var(--bg-2);
    border: 1px solid var(--border);
    padding: var(--space-4);
  }
  .section-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-2);
    margin-bottom: var(--space-3);
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }
  .section-meta {
    font-weight: 400;
    color: var(--text-3);
  }

  /* ── Target type chips */
  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin-top: var(--space-3);
  }
  .chip {
    padding: var(--space-1) var(--space-3);
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text-2);
    font-family: var(--font-ui);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.1s;
  }
  .chip:hover { border-color: var(--border-2); color: var(--text); }
  .chip.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }

  /* ── Mode cards */
  .mode-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-3);
  }
  .mode-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
    padding: var(--space-3) var(--space-4);
    border: 2px solid var(--border);
    background: var(--bg);
    cursor: pointer;
    text-align: left;
    font-family: var(--font-ui);
    transition: all 0.15s;
  }
  .mode-card:hover { border-color: var(--border-2); }
  .mode-card.active {
    border-color: var(--accent);
    background: var(--bg-2);
  }
  .mode-icon { font-size: 18px; }
  .mode-label {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--text);
  }
  .mode-desc {
    font-size: 11px;
    color: var(--text-2);
    line-height: 1.4;
  }

  /* ── Credential grid */
  .cred-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
  }

  /* ── Profile cards */
  .profile-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-3);
  }
  .profile-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-3);
    border: 2px solid var(--border);
    background: var(--bg);
    cursor: pointer;
    text-align: center;
    font-family: var(--font-ui);
    transition: all 0.15s;
  }
  .profile-card:hover { border-color: var(--border-2); }
  .profile-card.active {
    border-color: var(--accent);
    background: var(--bg-2);
  }
  .profile-name {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }
  .profile-count {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
  }
  .profile-desc {
    font-size: 10px;
    color: var(--text-2);
    line-height: 1.3;
  }

  /* ── Tool selection */
  .tool-controls {
    display: flex;
    gap: var(--space-2);
    margin-bottom: var(--space-3);
  }
  .tool-search {
    flex: 1;
  }
  .cat-row {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    margin-bottom: var(--space-3);
  }
  .cat-btn {
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text-2);
    padding: 3px 10px;
    font-size: 11px;
    font-family: var(--font-ui);
    cursor: pointer;
    transition: all 0.1s;
  }
  .cat-btn:hover { border-color: var(--border-2); }
  .cat-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }

  .tool-select-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1px;
    background: var(--border);
    max-height: 400px;
    overflow-y: auto;
  }
  .tool-item-select {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: var(--bg-2);
    border: none;
    cursor: pointer;
    text-align: left;
    font-family: var(--font-ui);
    transition: background 0.1s;
  }
  .tool-item-select:hover { background: var(--bg-3); }
  .tool-item-select.selected { background: var(--bg-3); }
  .tool-item-select.unavailable { opacity: 0.4; }
  .tool-check {
    font-size: 14px;
    color: var(--text-3);
    flex-shrink: 0;
  }
  .tool-item-select.selected .tool-check { color: var(--accent); }
  .tool-info {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
  }
  .tool-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
  }
  .tool-cat-label {
    font-size: 10px;
    color: var(--text-3);
    letter-spacing: 0.04em;
  }
  .tool-badge-na {
    margin-left: auto;
    font-size: 9px;
    color: var(--text-3);
    border: 1px solid var(--border);
    padding: 0 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  /* ── Footer / summary */
  .scan-footer {
    border-color: var(--accent);
  }
  .summary-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    margin-bottom: var(--space-3);
    font-size: 12px;
    color: var(--text-2);
  }
  .summary-item strong {
    color: var(--text);
  }
  .error-msg {
    color: var(--critical);
    font-size: 12px;
    margin-bottom: var(--space-3);
  }
  .btn-start {
    width: 100%;
    padding: var(--space-3);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }
</style>
