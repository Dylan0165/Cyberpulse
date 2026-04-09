<script lang="ts">
  import { onMount } from 'svelte';
  import { getSettings, saveSettings, checkTools } from '../lib/api';

  let settings: Record<string, any> = {
    deepseek_api_key: '',
    deepseek_model: 'deepseek-chat',
    deepseek_temperature: 0.3,
    nmap_timing: 'T4',
    max_threads: 50,
    scan_timeout: 300,
    wordlist_path: '/usr/share/wordlists/',
    shodan_api_key: '',
    abuseipdb_api_key: '',
    virustotal_api_key: '',
    hibp_api_key: '',
  };

  let tools: Record<string, boolean> = {};
  let saving = false;
  let saved = false;
  let loadingTools = true;

  onMount(async () => {
    try {
      const loaded = await getSettings();
      settings = { ...settings, ...loaded };
    } catch (e) {
      console.error('Failed to load settings:', e);
    }

    try {
      tools = await checkTools();
    } catch (e) {
      console.error('Failed to check tools:', e);
    }
    loadingTools = false;
  });

  async function handleSave() {
    saving = true;
    saved = false;
    try {
      await saveSettings(settings);
      saved = true;
      setTimeout(() => saved = false, 3000);
    } catch (e) {
      console.error('Failed to save settings:', e);
    }
    saving = false;
  }

  const toolList = [
    'nmap', 'nuclei', 'gobuster', 'sqlmap', 'testssl.sh',
    'whatweb', 'gitleaks', 'ffuf', 'feroxbuster', 'msfconsole',
    'apktool', 'nikto', 'wpscan',
  ];
</script>

<div class="page-header">
  <h1 class="page-title">Instellingen</h1>
</div>

<form on:submit|preventDefault={handleSave}>
  <!-- AI / API -->
  <div class="card" style="margin-bottom: var(--space-4);">
    <div class="card-header">
      <span class="card-title">AI / API</span>
    </div>
    <div class="form-group">
      <label for="deepseek-key">DeepSeek API Key</label>
      <input id="deepseek-key" type="password" bind:value={settings.deepseek_api_key} />
    </div>
    <div class="form-row">
      <div class="form-group">
        <label for="deepseek-model">Model</label>
        <select id="deepseek-model" bind:value={settings.deepseek_model}>
          <option value="deepseek-chat">deepseek-chat</option>
          <option value="deepseek-coder">deepseek-coder</option>
        </select>
      </div>
      <div class="form-group">
        <label for="deepseek-temp">Temperature</label>
        <input id="deepseek-temp" type="number" step="0.1" min="0" max="2" bind:value={settings.deepseek_temperature} />
      </div>
    </div>
  </div>

  <!-- Scanner -->
  <div class="card" style="margin-bottom: var(--space-4);">
    <div class="card-header">
      <span class="card-title">Scanner</span>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label for="nmap-timing">Nmap Timing</label>
        <select id="nmap-timing" bind:value={settings.nmap_timing}>
          <option value="T1">T1 (Sneaky)</option>
          <option value="T2">T2 (Polite)</option>
          <option value="T3">T3 (Normal)</option>
          <option value="T4">T4 (Aggressive)</option>
          <option value="T5">T5 (Insane)</option>
        </select>
      </div>
      <div class="form-group">
        <label for="max-threads">Max Threads</label>
        <input id="max-threads" type="number" min="1" max="200" bind:value={settings.max_threads} />
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label for="scan-timeout">Scan Timeout (s)</label>
        <input id="scan-timeout" type="number" min="30" bind:value={settings.scan_timeout} />
      </div>
      <div class="form-group">
        <label for="wordlist-path">Wordlist Pad</label>
        <input id="wordlist-path" type="text" bind:value={settings.wordlist_path} />
      </div>
    </div>
  </div>

  <!-- External API Keys -->
  <div class="card" style="margin-bottom: var(--space-4);">
    <div class="card-header">
      <span class="card-title">Externe API Keys (optioneel)</span>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label for="shodan-key">Shodan</label>
        <input id="shodan-key" type="password" bind:value={settings.shodan_api_key} />
      </div>
      <div class="form-group">
        <label for="abuseipdb-key">AbuseIPDB</label>
        <input id="abuseipdb-key" type="password" bind:value={settings.abuseipdb_api_key} />
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label for="vt-key">VirusTotal</label>
        <input id="vt-key" type="password" bind:value={settings.virustotal_api_key} />
      </div>
      <div class="form-group">
        <label for="hibp-key">HIBP</label>
        <input id="hibp-key" type="password" bind:value={settings.hibp_api_key} />
      </div>
    </div>
  </div>

  <!-- Tools Check -->
  <div class="card" style="margin-bottom: var(--space-4);">
    <div class="card-header">
      <span class="card-title">Tools Check</span>
    </div>
    {#if loadingTools}
      <p style="color: var(--text-2);">Controleren...</p>
    {:else}
      <div class="tools-grid">
        {#each toolList as tool}
          <div class="tool-item">
            {#if tools[tool]}
              <span class="check">✓</span>
            {:else}
              <span class="cross">✗</span>
            {/if}
            {tool}
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <div style="display: flex; align-items: center; gap: var(--space-3);">
    <button class="btn btn-primary" type="submit" disabled={saving}>
      {saving ? 'Opslaan...' : 'Opslaan'}
    </button>
    {#if saved}
      <span style="color: var(--accent); font-size: 12px;">✓ Opgeslagen</span>
    {/if}
  </div>
</form>
