<script lang="ts">
  import { onMount } from 'svelte';
  import { getAvailableTools } from '../lib/api';

  let toolsData: any = null;
  let loading = true;
  let error = '';

  // Filters
  let search = '';
  let activeCategory = 'all';

  const CATEGORY_LABELS: Record<string, string> = {
    all:               'Alle tools',
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
    crypto:            'Crypto / Stego',
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

  const TOOL_DESCRIPTIONS: Record<string, string> = {
    john: 'Probeert wachtwoorden te kraken uit versleutelde bestanden. Handig om te testen of wachtwoorden sterk genoeg zijn.',
    hashcat: 'Zeer snelle wachtwoordkraker die de grafische kaart gebruikt. Test of wachtwoorden bestand zijn tegen brute-force aanvallen.',
    hydra: 'Probeert automatisch in te loggen op diensten (zoals websites of e-mail) met veelgebruikte wachtwoorden.',
    crackmapexec: 'Test of Windows-netwerken kwetsbaar zijn door automatisch in te loggen en rechten te controleren.',
    medusa: 'Vergelijkbaar met Hydra: probeert wachtwoorden uit op netwerk-inlogpagina\'s om zwakke wachtwoorden te vinden.',
    fcrackzip: 'Kraakt wachtwoorden van beveiligde ZIP-bestanden om te testen of de beveiliging sterk genoeg is.',
    ophcrack: 'Kraakt Windows-wachtwoorden met behulp van regenboogtabellen — een slimme manier om wachtwoorden te achterhalen.',
    pdfcrack: 'Probeert het wachtwoord van beveiligde PDF-bestanden te raden.',
    masscan: 'Scant miljoenen IP-adressen razendsnel om te ontdekken welke diensten (poorten) open staan op een netwerk.',
    zmap: 'Scant het hele internet of grote netwerken in enkele minuten. Vindt welke apparaten online en bereikbaar zijn.',
    netdiscover: 'Ontdekt apparaten op een lokaal netwerk, zoals computers, printers en routers.',
    arpscan: 'Spoort alle apparaten op het lokale netwerk op door hun netwerkadres (MAC) op te vragen.',
    hping3: 'Stuurt aangepaste netwerkpakketten om firewalls te testen en te kijken hoe een systeem reageert.',
    unicornscan: 'Snelle netwerkscanner die veel poorten tegelijk kan controleren op open diensten.',
    sqlmap: 'Zoekt automatisch naar SQL-injectie kwetsbaarheden — een veelvoorkomend beveiligingslek in websites.',
    nikto: 'Scant webservers op bekende beveiligingsproblemen, verouderde software en onveilige instellingen.',
    wpscan: 'Controleert WordPress-websites op kwetsbaarheden in thema\'s, plugins en instellingen.',
    gobuster: 'Zoekt naar verborgen pagina\'s en mappen op een website die niet zichtbaar zijn in het menu.',
    nuclei: 'Scant websites en servers met duizenden bekende kwetsbaarheids-sjablonen.',
    wfuzz: 'Test websites door automatisch allerlei invoer te proberen om verborgen pagina\'s of zwakke plekken te vinden.',
    xsstrike: 'Zoekt naar Cross-Site Scripting (XSS) kwetsbaarheden waarmee aanvallers code in een website kunnen plaatsen.',
    commix: 'Test of een website kwetsbaar is voor command injection — waarbij een aanvaller opdrachten kan uitvoeren op de server.',
    arjun: 'Ontdekt verborgen parameters in website-URL\'s die mogelijk misbruikt kunnen worden.',
    skipfish: 'Maakt een volledige kaart van een website en zoekt automatisch naar beveiligingsproblemen.',
    'aireplay-ng': 'Test de beveiliging van wifi-netwerken door netwerkverkeer te manipuleren en opnieuw te versturen.',
    reaver: 'Probeert de WPS-pincode van wifi-routers te kraken om zo het wifi-wachtwoord te achterhalen.',
    wash: 'Scant op wifi-netwerken die WPS ingeschakeld hebben, wat een beveiligingsrisico kan zijn.',
    kismet: 'Luistert naar alle wifi-signalen in de buurt en brengt draadloze netwerken en apparaten in kaart.',
    tshark: 'Vangt netwerkverkeer op en analyseert het — de commandoregel-versie van Wireshark.',
    tcpdump: 'Basisgereedschap om netwerkverkeer op te vangen en te bekijken.',
    bettercap: 'Alles-in-één tool voor netwerkaanvallen: kan verkeer onderscheppen, wifi hacken en netwerken scannen.',
    responder: 'Onderschept inloggegevens op een Windows-netwerk door zich voor te doen als een netwerkdienst.',
    arpspoof: 'Vervalst netwerkberichten zodat verkeer van andere apparaten via jouw computer loopt.',
    ettercap: 'Onderschept en analyseert netwerkverkeer tussen twee apparaten.',
    macchanger: 'Verandert het hardware-adres (MAC) van je netwerkkaart zodat je apparaat niet herkend wordt.',
    theharvester: 'Verzamelt e-mailadressen, domeinnamen en andere publieke informatie over een bedrijf.',
    amass: 'Brengt alle subdomeinen van een website in kaart. Ontdekt verborgen diensten die mogelijk kwetsbaar zijn.',
    dnsrecon: 'Onderzoekt DNS-instellingen van een domein en zoekt naar verkeerd geconfigureerde naamservers.',
    fierce: 'Scant snel de DNS-configuratie van een domein om subdomeinen en IP-adressen te vinden.',
    spiderfoot: 'Verzamelt automatisch alle publiek beschikbare informatie over een domein, persoon of bedrijf.',
    shodan: 'Doorzoekt een database van alle apparaten die aan het internet hangen — van webcams tot servers.',
    'recon-ng': 'Uitgebreid onderzoeksplatform dat informatie verzamelt uit openbare bronnen.',
    maltego: 'Maakt visuele grafieken van verbanden tussen personen, domeinen, e-mails en bedrijven.',
    searchsploit: 'Doorzoekt een offline database van bekende kwetsbaarheden en exploits.',
    impacket: 'Set Python-tools om Windows-netwerken aan te vallen en te testen.',
    'evil-winrm': 'Maakt verbinding met Windows-systemen via WinRM om te testen of ze op afstand overgenomen kunnen worden.',
    certipy: 'Test de beveiliging van digitale certificaten in een Windows Active Directory-netwerk.',
    'bloodhound-reader': 'Analyseert de structuur van een Windows-netwerk en toont hoe een aanvaller van punt A naar B kan komen.',
    'linpeas-parser': 'Analyseert de uitvoer van LinPEAS — zoekt naar manieren om hogere rechten te krijgen op Linux.',
    mimikatz: 'Haalt wachtwoorden en inloggegevens uit het geheugen van Windows.',
    'winpeas-parser': 'Analyseert de uitvoer van WinPEAS — zoekt naar manieren om hogere rechten te krijgen op Windows.',
    volatility3: 'Analyseert het werkgeheugen (RAM) van een computer om te zien welke programma\'s draaiden.',
    binwalk: 'Zoekt naar verborgen bestanden die ingebed zijn in andere bestanden, zoals firmware-images.',
    exiftool: 'Leest verborgen metadata uit bestanden (wie het maakte, wanneer, met welk apparaat, etc.).',
    strings: 'Haalt leesbare tekst uit bestanden — handig om te zien of er wachtwoorden of URLs verborgen zitten.',
    foremost: 'Herstelt verwijderde bestanden uit een harde schijf of geheugenkaart.',
    steghide: 'Detecteert en haalt verborgen berichten uit afbeeldingen en audiobestanden.',
    radare2: 'Analyseert programma\'s op hun laagste niveau (machinecode) om te begrijpen hoe ze werken.',
    objdump: 'Toont de inhoud van gecompileerde programmabestanden.',
    strace: 'Volgt alle systeemoproepen die een programma doet — laat zien welke bestanden het gebruikt.',
    ghidra: 'Krachtige tool (van de NSA) die gecompileerde programma\'s omzet naar leesbare code voor analyse.',
    pwntools: 'Python-bibliotheek voor het schrijven en testen van exploits.',
    ropper: 'Vindt bruikbare code-fragmenten in programma\'s die misbruikt kunnen worden.',
    lynis: 'Controleert Linux/Unix-systemen op beveiligingsinstellingen en geeft advies.',
    trivy: 'Scant Docker-containers en code-afhankelijkheden op bekende kwetsbaarheden.',
    grype: 'Zoekt in softwarepakketten naar bekende beveiligingslekken.',
    chkrootkit: 'Controleert of er kwaadaardige software (rootkits) verborgen zit op een Linux-systeem.',
    openvas: 'Uitgebreide kwetsbaarheidsscanner die duizenden beveiligingschecks uitvoert.',
    hashid: 'Herkent het type versleuteling (hash) dat gebruikt is om een wachtwoord te beveiligen.',
    hash_identifier: 'Vergelijkbaar met hashID: identificeert welk type versleuteling gebruikt is.',
    cyberchef: 'Online \'Zwitsers zakmes\' voor versleuteling, decodering en data-analyse.',
    stegseek: 'Zoekt razendsnel naar verborgen berichten in afbeeldingen.',
    featherduster: 'Analyseert versleutelde berichten automatisch om de gebruikte versleutelmethode te achterhalen.',
  };

  onMount(async () => {
    try {
      toolsData = await getAvailableTools();
    } catch (e: any) {
      error = e.message ?? 'Kon tools niet laden';
    }
    loading = false;
  });

  $: allTools = toolsData
    ? Object.values(toolsData as Record<string, any>)
    : [];

  $: categories = allTools.length
    ? ['all', ...[...new Set(allTools.map((t: any) => t.category).filter(Boolean))].sort()]
    : ['all'];

  $: filtered = allTools.filter((t: any) => {
    const matchCat = activeCategory === 'all' || t.category === activeCategory;
    const matchSearch = !search ||
      t.name?.toLowerCase().includes(search.toLowerCase()) ||
      t.display_name?.toLowerCase().includes(search.toLowerCase()) ||
      (TOOL_DESCRIPTIONS[t.name] ?? '').toLowerCase().includes(search.toLowerCase());
    return matchCat && matchSearch;
  });

  $: availableCount = allTools.filter((t: any) => t.available).length;
  $: categoryCount = (cat: string) => {
    if (cat === 'all') return allTools.length;
    return allTools.filter((t: any) => t.category === cat).length;
  };
</script>

<div class="page-header">
  <h1 class="page-title">Tools</h1>
  <span class="page-meta">{availableCount} / {allTools.length} beschikbaar op dit systeem</span>
</div>

{#if loading}
  <div style="padding: var(--space-4); color: var(--text-3);">Tools laden...</div>
{:else if error}
  <div style="padding: var(--space-4); color: var(--critical);">Fout: {error}</div>
{:else}

  <!-- ── Search -->
  <div class="search-bar">
    <input
      type="text"
      placeholder="Zoek op naam of beschrijving..."
      bind:value={search}
    />
  </div>

  <!-- ── Categories -->
  <div class="cat-row">
    {#each categories as cat}
      <button
        class="cat-btn"
        class:active={activeCategory === cat}
        on:click={() => activeCategory = cat}
      >
        {CATEGORY_ICONS[cat] ?? ''} {CATEGORY_LABELS[cat] ?? cat}
        <span class="cat-count">{categoryCount(cat)}</span>
      </button>
    {/each}
  </div>

  <!-- ── Tool grid -->
  {#if filtered.length === 0}
    <div style="color: var(--text-3); padding: var(--space-4);">Geen tools gevonden.</div>
  {:else}
    <div class="tool-grid">
      {#each filtered as tool}
        <div class="tool-card" class:unavailable={!tool.available}>
          <div class="tool-header">
            <span class="tool-name">{tool.display_name || tool.name}</span>
            {#if tool.available}
              <span class="tool-status available">●</span>
            {:else}
              <span class="tool-status na">○</span>
            {/if}
          </div>
          <div class="tool-cat">
            {CATEGORY_ICONS[tool.category] ?? ''} {CATEGORY_LABELS[tool.category] ?? tool.category}
          </div>
          {#if TOOL_DESCRIPTIONS[tool.name]}
            <div class="tool-desc">{TOOL_DESCRIPTIONS[tool.name]}</div>
          {/if}
          <div class="tool-id">{tool.name}</div>
        </div>
      {/each}
    </div>
  {/if}

{/if}

<style>
  .search-bar {
    margin-bottom: var(--space-3);
  }
  .search-bar input {
    width: 100%;
  }

  .cat-row {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
    margin-bottom: var(--space-4);
  }
  .cat-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text-2);
    padding: 4px 10px;
    font-size: 11px;
    font-family: var(--font-ui);
    cursor: pointer;
    transition: all 0.1s;
  }
  .cat-btn:hover { border-color: var(--border-2); color: var(--text); }
  .cat-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
  .cat-count {
    font-size: 9px;
    opacity: 0.6;
  }

  .tool-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 1px;
    background: var(--border);
  }

  .tool-card {
    background: var(--bg-2);
    padding: var(--space-3);
    display: flex;
    flex-direction: column;
    gap: 4px;
    transition: background 0.1s;
  }
  .tool-card:hover { background: var(--bg-3); }
  .tool-card.unavailable { opacity: 0.4; }

  .tool-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .tool-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    font-family: var(--font-ui);
  }
  .tool-status { font-size: 10px; }
  .tool-status.available { color: var(--accent); }
  .tool-status.na { color: var(--text-3); }

  .tool-cat {
    font-size: 10px;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: .06em;
  }
  .tool-desc {
    font-size: 11px;
    color: var(--text-2);
    line-height: 1.4;
    flex: 1;
  }
  .tool-id {
    font-size: 10px;
    color: var(--text-3);
    font-family: var(--font-ui);
    opacity: 0.5;
  }
</style>
