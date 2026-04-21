"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toolsApi } from "@/lib/api";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Play,
  Square,
  Search,
  Wrench,
  Globe,
  Wifi,
  Eye,
  Lock,
  Bug,
  Server,
  HardDrive,
  Binary,
  ShieldAlert,
  KeyRound,
  Terminal,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const CATEGORY_ICONS: Record<string, any> = {
  password_cracking: KeyRound,
  password: KeyRound,
  network_scanning: Globe,
  web_exploitation: Globe,
  web: Globe,
  wireless: Wifi,
  sniffing: Eye,
  osint: Search,
  exploitation: Bug,
  post_exploitation: Server,
  post_exploit: Server,
  forensics: HardDrive,
  reverse_engineering: Binary,
  reversing: Binary,
  vuln_analysis: ShieldAlert,
  crypto: Lock,
};

const CATEGORY_LABELS: Record<string, string> = {
  password_cracking: "Password Attacks",
  password: "Password Attacks",
  network_scanning: "Network Scanning",
  web_exploitation: "Web Application",
  web: "Web Application",
  wireless: "Wireless",
  sniffing: "Sniffing & Spoofing",
  osint: "OSINT & Recon",
  exploitation: "Exploitation",
  post_exploitation: "Post-Exploitation",
  post_exploit: "Post-Exploitation",
  forensics: "Forensics",
  reverse_engineering: "Reverse Engineering",
  reversing: "Reverse Engineering",
  vuln_analysis: "Vulnerability Analysis",
  crypto: "Cryptography",
};

const TOOL_DESCRIPTIONS: Record<string, string> = {
  john: "Probeert wachtwoorden te kraken uit versleutelde bestanden. Handig om te testen of wachtwoorden sterk genoeg zijn.",
  hashcat: "Zeer snelle wachtwoordkraker die de grafische kaart gebruikt. Test of wachtwoorden bestand zijn tegen brute-force aanvallen.",
  hydra: "Probeert automatisch in te loggen op diensten (zoals websites of e-mail) met veelgebruikte wachtwoorden.",
  crackmapexec: "Test of Windows-netwerken kwetsbaar zijn door automatisch in te loggen en rechten te controleren.",
  medusa: "Vergelijkbaar met Hydra: probeert wachtwoorden uit op netwerk-inlogpagina's om zwakke wachtwoorden te vinden.",
  fcrackzip: "Kraakt wachtwoorden van beveiligde ZIP-bestanden om te testen of de beveiliging sterk genoeg is.",
  ophcrack: "Kraakt Windows-wachtwoorden met behulp van regenboogtabellen.",
  pdfcrack: "Probeert het wachtwoord van beveiligde PDF-bestanden te raden.",
  masscan: "Scant miljoenen IP-adressen razendsnel om te ontdekken welke diensten open staan.",
  zmap: "Scant het hele internet of grote netwerken in enkele minuten.",
  netdiscover: "Ontdekt apparaten op een lokaal netwerk, zoals computers, printers en routers.",
  arpscan: "Spoort alle apparaten op het lokale netwerk op door hun netwerkadres (MAC) op te vragen.",
  hping3: "Stuurt aangepaste netwerkpakketten om firewalls te testen.",
  unicornscan: "Snelle netwerkscanner die veel poorten tegelijk kan controleren.",
  sqlmap: "Zoekt automatisch naar SQL-injectie kwetsbaarheden in websites.",
  nikto: "Scant webservers op bekende beveiligingsproblemen en verouderde software.",
  wpscan: "Controleert WordPress-websites op kwetsbaarheden in thema's, plugins en instellingen.",
  gobuster: "Zoekt naar verborgen pagina's en mappen op een website.",
  nuclei: "Scant websites en servers met duizenden bekende kwetsbaarheids-sjablonen.",
  wfuzz: "Test websites door automatisch allerlei invoer te proberen.",
  xsstrike: "Zoekt naar Cross-Site Scripting (XSS) kwetsbaarheden.",
  commix: "Test of een website kwetsbaar is voor command injection.",
  arjun: "Ontdekt verborgen parameters in website-URL's.",
  skipfish: "Maakt een volledige kaart van een website en zoekt naar beveiligingsproblemen.",
  "aireplay-ng": "Test de beveiliging van wifi-netwerken door netwerkverkeer te manipuleren.",
  reaver: "Probeert de WPS-pincode van wifi-routers te kraken.",
  wash: "Scant op wifi-netwerken die WPS ingeschakeld hebben.",
  kismet: "Luistert naar alle wifi-signalen in de buurt en brengt draadloze netwerken in kaart.",
  tshark: "Vangt netwerkverkeer op en analyseert het.",
  tcpdump: "Basisgereedschap om netwerkverkeer op te vangen en te bekijken.",
  bettercap: "Alles-in-één tool voor netwerkaanvallen.",
  responder: "Onderschept inloggegevens op een Windows-netwerk.",
  arpspoof: "Vervalst netwerkberichten zodat verkeer via jouw computer loopt.",
  ettercap: "Onderschept en analyseert netwerkverkeer tussen twee apparaten.",
  macchanger: "Verandert het hardware-adres (MAC) van je netwerkkaart.",
  theharvester: "Verzamelt e-mailadressen, domeinnamen en andere publieke informatie.",
  amass: "Brengt alle subdomeinen van een website in kaart.",
  dnsrecon: "Onderzoekt DNS-instellingen van een domein.",
  fierce: "Scant snel de DNS-configuratie van een domein.",
  spiderfoot: "Verzamelt automatisch alle publiek beschikbare informatie over een domein.",
  shodan: "Doorzoekt een database van alle apparaten die aan het internet hangen.",
  "recon-ng": "Uitgebreid onderzoeksplatform dat informatie verzamelt uit openbare bronnen.",
  maltego: "Maakt visuele grafieken van verbanden tussen personen, domeinen en bedrijven.",
  searchsploit: "Doorzoekt een offline database van bekende kwetsbaarheden.",
  impacket: "Set Python-tools om Windows-netwerken aan te vallen en te testen.",
  "evil-winrm": "Maakt verbinding met Windows-systemen via WinRM.",
  certipy: "Test de beveiliging van digitale certificaten in Active Directory.",
  "bloodhound-reader": "Analyseert de structuur van een Windows-netwerk.",
  "linpeas-parser": "Analyseert de uitvoer van LinPEAS op Linux privilege escalation.",
  mimikatz: "Haalt wachtwoorden en inloggegevens uit het geheugen van Windows.",
  "winpeas-parser": "Analyseert de uitvoer van WinPEAS op Windows privilege escalation.",
  volatility3: "Analyseert het werkgeheugen (RAM) van een computer.",
  binwalk: "Zoekt naar verborgen bestanden die ingebed zijn in andere bestanden.",
  exiftool: "Leest verborgen metadata uit bestanden.",
  strings: "Haalt leesbare tekst uit bestanden.",
  foremost: "Herstelt verwijderde bestanden van een harde schijf.",
  steghide: "Detecteert en haalt verborgen berichten uit afbeeldingen.",
  radare2: "Analyseert programma's op hun laagste niveau (machinecode).",
  objdump: "Toont de inhoud van gecompileerde programmabestanden.",
  strace: "Volgt alle systeemoproepen die een programma doet.",
  ghidra: "Krachtige tool (van de NSA) die programma's omzet naar leesbare code.",
  pwntools: "Python-bibliotheek voor het schrijven en testen van exploits.",
  ropper: "Vindt bruikbare code-fragmenten voor geheugen-aanvallen.",
  lynis: "Controleert Linux/Unix-systemen op beveiligingsinstellingen.",
  trivy: "Scant Docker-containers en code-afhankelijkheden op kwetsbaarheden.",
  grype: "Zoekt in softwarepakketten naar bekende beveiligingslekken.",
  chkrootkit: "Controleert of er kwaadaardige software (rootkits) op een Linux-systeem zit.",
  openvas: "Uitgebreide kwetsbaarheidsscanner die duizenden beveiligingschecks uitvoert.",
  hashid: "Herkent het type versleuteling (hash) dat gebruikt is.",
  hash_identifier: "Identificeert welk type versleuteling gebruikt is voor een hash.",
  cyberchef: "Online 'Zwitsers zakmes' voor versleuteling en data-analyse.",
  stegseek: "Zoekt razendsnel naar verborgen berichten in afbeeldingen.",
  featherduster: "Analyseert versleutelde berichten automatisch.",
};

interface ToolInfo {
  name: string;
  display_name: string;
  category: string;
  available: boolean;
  implementation: string;
  default_timeout: number;
  resource_profile: {
    estimated_ram_mb: number;
    estimated_duration_s: number;
    requires_gpu: boolean;
    cpu_intensive: boolean;
  };
}

interface ScanEvent {
  type: string;
  tool?: string;
  display_name?: string;
  index?: number;
  total?: number;
  findings_count?: number;
  duration?: number;
  skip_reason?: string;
  error?: string;
  total_findings?: number;
  tools_run?: number;
  message?: string;
}

const SCAN_MODE_INFO = {
  blackbox: {
    label: "Blackbox",
    description: "Extern perspectief — geen kennis of toegang tot systeem",
    color: "text-red-500",
    bg: "bg-red-500/10 border-red-500/30",
    activeBg: "bg-red-500 text-white border-red-500",
  },
  graybox: {
    label: "Graybox",
    description: "Gedeeltelijke kennis — beperkte inloggegevens beschikbaar",
    color: "text-yellow-500",
    bg: "bg-yellow-500/10 border-yellow-500/30",
    activeBg: "bg-yellow-500 text-white border-yellow-500",
  },
  whitebox: {
    label: "Whitebox",
    description: "Volledige toegang — broncode, SSH, configuratie beschikbaar",
    color: "text-green-500",
    bg: "bg-green-500/10 border-green-500/30",
    activeBg: "bg-green-500 text-white border-green-500",
  },
};

export default function ToolsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set());
  const [target, setTarget] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null);
  const [scanMode, setScanMode] = useState<"blackbox" | "graybox" | "whitebox">("blackbox");
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [scanEvents, setScanEvents] = useState<ScanEvent[]>([]);
  const [scanRunning, setScanRunning] = useState(false);
  const [showLog, setShowLog] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const { data: toolsData, isLoading: toolsLoading } = useQuery({
    queryKey: ["tools-available"],
    queryFn: () => toolsApi.available().then((r) => r.data as Record<string, ToolInfo>),
    retry: 2,
  });

  const { data: profilesData } = useQuery({
    queryKey: ["tools-profiles"],
    queryFn: () => toolsApi.profiles().then((r) => r.data as Record<string, string[]>),
    retry: 2,
  });

  const startScanMutation = useMutation({
    mutationFn: (data: { target: string; tools?: string[]; profile?: string; scan_mode: string }) =>
      toolsApi.startScan(data),
    onSuccess: (res) => {
      const { scan_id, tools } = res.data;
      setActiveScanId(scan_id);
      setScanRunning(true);
      setScanEvents([{ type: "scan_queued", message: `Scan gestart voor ${tools?.length ?? 0} tools` }]);
      setShowLog(true);
      startSSEStream(scan_id);
    },
  });

  const startSSEStream = (scanId: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    const url = `/api/tools/scan/${scanId}/stream`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: ScanEvent = JSON.parse(e.data);
        setScanEvents((prev) => [...prev, event]);
        if (event.type === "all_done" || event.type === "tools_complete") {
          setScanRunning(false);
          es.close();
        }
      } catch {}
    };

    es.onerror = () => {
      setScanRunning(false);
      setScanEvents((prev) => [...prev, { type: "error", message: "Verbinding verbroken" }]);
      es.close();
    };
  };

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [scanEvents]);

  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  const tools = toolsData ? Object.values(toolsData) : [];

  const categories = new Map<string, ToolInfo[]>();
  tools.forEach((tool) => {
    const cat = tool.category;
    if (!categories.has(cat)) categories.set(cat, []);
    categories.get(cat)!.push(tool);
  });

  const filteredTools = tools.filter((t) => {
    const matchesSearch =
      !searchQuery ||
      t.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCat = !selectedCategory || t.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const filteredCategories = new Map<string, ToolInfo[]>();
  filteredTools.forEach((tool) => {
    const cat = tool.category;
    if (!filteredCategories.has(cat)) filteredCategories.set(cat, []);
    filteredCategories.get(cat)!.push(tool);
  });

  const toggleTool = (name: string) => {
    setSelectedTools((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectProfile = (profileName: string) => {
    if (!profilesData) return;
    const toolNames = profilesData[profileName] || [];
    setSelectedTools(new Set(toolNames));
    setSelectedProfile(profileName);
  };

  const handleStartScan = () => {
    if (!target.trim()) return;
    const payload: any = { target: target.trim(), scan_mode: scanMode };
    if (selectedTools.size > 0) {
      payload.tools = Array.from(selectedTools);
    } else if (selectedProfile) {
      payload.profile = selectedProfile;
    } else {
      return;
    }
    startScanMutation.mutate(payload);
  };

  const handleStopScan = () => {
    eventSourceRef.current?.close();
    setScanRunning(false);
    setScanEvents((prev) => [...prev, { type: "stopped", message: "Scan handmatig gestopt" }]);
  };

  const availableCount = tools.filter((t) => t.available).length;
  const totalCount = tools.length;

  const renderEvent = (event: ScanEvent, idx: number) => {
    const colors: Record<string, string> = {
      tool_start: "text-blue-400",
      tool_done: "text-green-400",
      tool_skipped: "text-yellow-400",
      tool_error: "text-red-400",
      tools_start: "text-purple-400",
      tools_complete: "text-green-300",
      all_done: "text-green-300",
      error: "text-red-400",
      stopped: "text-orange-400",
      scan_queued: "text-blue-300",
    };
    const color = colors[event.type] || "text-muted-foreground";

    let msg = "";
    switch (event.type) {
      case "tools_start":
        msg = `▶ Starten: ${event.total} tools`;
        break;
      case "tool_start":
        msg = `[${event.index}/${event.total}] ⏳ ${event.display_name}...`;
        break;
      case "tool_done":
        msg = `[${event.index}/${event.total}] ✓ ${event.display_name} — ${event.findings_count} bevindingen (${event.duration}s)`;
        break;
      case "tool_skipped":
        msg = `[${event.index}/${event.total}] ⊘ ${event.display_name} — overgeslagen: ${event.skip_reason}`;
        break;
      case "tool_error":
        msg = `[${event.index}/${event.total}] ✗ ${event.display_name} — fout: ${event.error}`;
        break;
      case "tools_complete":
        msg = `✓ Klaar — ${event.total_findings} bevindingen in ${event.tools_run} tools`;
        break;
      case "all_done":
        msg = "✓ Scan volledig afgerond";
        break;
      default:
        msg = event.message || event.type;
    }

    return (
      <div key={idx} className={`font-mono text-xs ${color}`}>
        {msg}
      </div>
    );
  };

  if (toolsLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Tools laden via CyberPulse engine...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Wrench className="h-7 w-7 text-primary" />
            Kali Tools
          </h1>
          <p className="text-muted-foreground mt-1">
            {availableCount} van {totalCount} tools beschikbaar op dit systeem
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <div className="flex items-center gap-1">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <span>{availableCount} beschikbaar</span>
          </div>
          <div className="flex items-center gap-1">
            <XCircle className="h-4 w-4 text-red-400" />
            <span>{totalCount - availableCount} niet geïnstalleerd</span>
          </div>
        </div>
      </div>

      {/* Scan configuratie */}
      <div className="rounded-xl border bg-card p-5 shadow-sm space-y-4">
        <h2 className="text-lg font-semibold">Tool Scan Configureren</h2>

        {/* Scan Mode selector */}
        <div>
          <p className="text-sm text-muted-foreground mb-2 font-medium">Scan modus</p>
          <div className="grid grid-cols-3 gap-2">
            {(["blackbox", "graybox", "whitebox"] as const).map((mode) => {
              const info = SCAN_MODE_INFO[mode];
              const active = scanMode === mode;
              return (
                <button
                  key={mode}
                  onClick={() => setScanMode(mode)}
                  className={`rounded-lg border p-3 text-left transition-all ${
                    active ? info.activeBg : info.bg + " hover:opacity-90"
                  }`}
                >
                  <div className={`text-sm font-semibold ${active ? "" : info.color}`}>
                    {info.label}
                  </div>
                  <div className={`text-xs mt-0.5 ${active ? "opacity-80" : "text-muted-foreground"}`}>
                    {info.description}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Target + Start */}
        <div className="flex gap-3">
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="Target (bijv. 192.168.1.0/24 of testlab.intern)"
            className="flex-1 rounded-lg border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          {scanRunning ? (
            <button
              onClick={handleStopScan}
              className="flex items-center gap-2 rounded-lg bg-red-500 px-5 py-2 text-sm font-medium text-white hover:bg-red-600 transition-colors"
            >
              <Square className="h-4 w-4" />
              Stop
            </button>
          ) : (
            <button
              onClick={handleStartScan}
              disabled={!target.trim() || (selectedTools.size === 0 && !selectedProfile) || startScanMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {startScanMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Scan ({selectedTools.size > 0 ? selectedTools.size : selectedProfile ? "profiel" : "0"} tools)
            </button>
          )}
        </div>

        {/* Profiles */}
        {profilesData && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(profilesData).map(([name, toolList]) => (
              <button
                key={name}
                onClick={() => selectProfile(name)}
                className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                  selectedProfile === name
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground border-border hover:border-primary"
                }`}
              >
                {name.replace(/_/g, " ")} ({toolList.length})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Live output log */}
      {scanEvents.length > 0 && (
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
          <button
            onClick={() => setShowLog((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-3 hover:bg-accent transition-colors"
          >
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Terminal className="h-4 w-4 text-primary" />
              Live Scan Output
              {scanRunning && <Loader2 className="h-3 w-3 animate-spin text-primary" />}
              {activeScanId && (
                <span className="text-xs font-normal text-muted-foreground">ID: {activeScanId}</span>
              )}
            </div>
            {showLog ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {showLog && (
            <div className="bg-black/90 p-4 max-h-64 overflow-y-auto space-y-0.5">
              {scanEvents.map((ev, i) => renderEvent(ev, i))}
              <div ref={logEndRef} />
            </div>
          )}
        </div>
      )}

      {/* Search & Category filter */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Zoek op naam of beschrijving..."
            className="w-full rounded-lg border bg-background pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
              !selectedCategory
                ? "bg-primary text-primary-foreground"
                : "bg-card text-muted-foreground hover:bg-accent border"
            }`}
          >
            Alle tools {totalCount}
          </button>
          {Array.from(categories.keys())
            .sort()
            .map((cat) => {
              const Icon = CATEGORY_ICONS[cat] || Wrench;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
                  className={`flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                    selectedCategory === cat
                      ? "bg-primary text-primary-foreground"
                      : "bg-card text-muted-foreground hover:bg-accent border"
                  }`}
                >
                  <Icon className="h-3 w-3" />
                  {CATEGORY_LABELS[cat] || cat}
                </button>
              );
            })}
        </div>
      </div>

      {/* Tools grid per category */}
      {Array.from(filteredCategories.entries())
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([category, catTools]) => {
          const Icon = CATEGORY_ICONS[category] || Wrench;
          return (
            <div key={category} className="space-y-3">
              <h3 className="flex items-center gap-2 text-lg font-semibold">
                <Icon className="h-5 w-5 text-primary" />
                {CATEGORY_LABELS[category] || category}
                <span className="text-sm font-normal text-muted-foreground">
                  ({catTools.filter((t) => t.available).length}/{catTools.length} beschikbaar)
                </span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {catTools.map((tool) => (
                  <div
                    key={tool.name}
                    onClick={() => tool.available && toggleTool(tool.name)}
                    className={`relative rounded-xl border p-4 transition-all ${
                      selectedTools.has(tool.name)
                        ? "border-primary bg-primary/5 ring-1 ring-primary cursor-pointer"
                        : tool.available
                        ? "border-border bg-card hover:border-primary/50 hover:shadow-sm cursor-pointer"
                        : "border-border bg-muted/30 opacity-50 cursor-not-allowed"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium text-sm">{tool.display_name}</h4>
                        <p className="text-xs text-muted-foreground mt-0.5 font-mono">{tool.name}</p>
                      </div>
                      {tool.available ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                      )}
                    </div>
                    {TOOL_DESCRIPTIONS[tool.name] && (
                      <p className="mt-2 text-xs text-muted-foreground leading-relaxed line-clamp-3">
                        {TOOL_DESCRIPTIONS[tool.name]}
                      </p>
                    )}
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                      <span className="inline-flex items-center rounded-md bg-background px-2 py-0.5 text-[10px] font-medium border">
                        {tool.implementation}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        ~{tool.resource_profile.estimated_duration_s}s
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {tool.resource_profile.estimated_ram_mb}MB
                      </span>
                      {tool.resource_profile.requires_gpu && (
                        <span className="inline-flex items-center rounded-md bg-yellow-500/10 text-yellow-600 px-2 py-0.5 text-[10px] font-medium">
                          GPU
                        </span>
                      )}
                      {tool.resource_profile.cpu_intensive && (
                        <span className="inline-flex items-center rounded-md bg-orange-500/10 text-orange-600 px-2 py-0.5 text-[10px] font-medium">
                          CPU
                        </span>
                      )}
                    </div>
                    {selectedTools.has(tool.name) && (
                      <div className="absolute top-2 right-2 h-2 w-2 rounded-full bg-primary" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
    </div>
  );
}
