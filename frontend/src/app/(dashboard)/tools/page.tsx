"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toolsApi } from "@/lib/api";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Play,
  Filter,
  Search,
  Wrench,
  Shield,
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
} from "lucide-react";

const CATEGORY_ICONS: Record<string, any> = {
  password: KeyRound,
  network_scanning: Globe,
  web: Globe,
  wireless: Wifi,
  sniffing: Eye,
  osint: Search,
  exploitation: Bug,
  post_exploit: Server,
  forensics: HardDrive,
  reversing: Binary,
  vuln_analysis: ShieldAlert,
  crypto: Lock,
};

const CATEGORY_LABELS: Record<string, string> = {
  password: "Password Attacks",
  network_scanning: "Network Scanning",
  web: "Web Application",
  wireless: "Wireless",
  sniffing: "Sniffing & Spoofing",
  osint: "OSINT & Recon",
  exploitation: "Exploitation",
  post_exploit: "Post-Exploitation",
  forensics: "Forensics",
  reversing: "Reverse Engineering",
  vuln_analysis: "Vulnerability Analysis",
  crypto: "Cryptography",
};

// Eenvoudige uitleg per tool, begrijpelijk voor niet-technische mensen
const TOOL_DESCRIPTIONS: Record<string, string> = {
  // Password Attacks
  john: "Probeert wachtwoorden te kraken uit versleutelde bestanden. Handig om te testen of wachtwoorden sterk genoeg zijn.",
  hashcat: "Zeer snelle wachtwoordkraker die de grafische kaart gebruikt. Test of wachtwoorden bestand zijn tegen brute-force aanvallen.",
  hydra: "Probeert automatisch in te loggen op diensten (zoals websites of e-mail) met veelgebruikte wachtwoorden.",
  crackmapexec: "Test of Windows-netwerken kwetsbaar zijn door automatisch in te loggen en rechten te controleren.",
  medusa: "Vergelijkbaar met Hydra: probeert wachtwoorden uit op netwerk-inlogpagina's om zwakke wachtwoorden te vinden.",
  fcrackzip: "Kraakt wachtwoorden van beveiligde ZIP-bestanden om te testen of de beveiliging sterk genoeg is.",
  ophcrack: "Kraakt Windows-wachtwoorden met behulp van regenboogtabellen — een slimme manier om wachtwoorden te achterhalen.",
  pdfcrack: "Probeert het wachtwoord van beveiligde PDF-bestanden te raden.",

  // Network Scanning
  masscan: "Scant miljoenen IP-adressen razendsnel om te ontdekken welke diensten (poorten) open staan op een netwerk.",
  zmap: "Scant het hele internet of grote netwerken in enkele minuten. Vindt welke apparaten online en bereikbaar zijn.",
  netdiscover: "Ontdekt apparaten op een lokaal netwerk, zoals computers, printers en routers.",
  arpscan: "Spoort alle apparaten op het lokale netwerk op door hun netwerkadres (MAC) op te vragen.",
  hping3: "Stuurt aangepaste netwerkpakketten om firewalls te testen en te kijken hoe een systeem reageert.",
  unicornscan: "Snelle netwerkscanner die veel poorten tegelijk kan controleren op open diensten.",

  // Web Application
  sqlmap: "Zoekt automatisch naar SQL-injectie kwetsbaarheden — een veelvoorkomend beveiligingslek in websites waarmee aanvallers de database kunnen uitlezen.",
  nikto: "Scant webservers op bekende beveiligingsproblemen, verouderde software en onveilige instellingen.",
  wpscan: "Controleert WordPress-websites op kwetsbaarheden in thema's, plugins en instellingen.",
  gobuster: "Zoekt naar verborgen pagina's en mappen op een website die niet zichtbaar zijn in het menu.",
  nuclei: "Scant websites en servers met duizenden bekende kwetsbaarheids-sjablonen. Vindt snel bekende beveiligslekken.",
  wfuzz: "Test websites door automatisch allerlei invoer te proberen om verborgen pagina's of zwakke plekken te vinden.",
  xsstrike: "Zoekt naar Cross-Site Scripting (XSS) kwetsbaarheden — een lek waarmee aanvallers kwaadaardige code in een website kunnen plaatsen.",
  commix: "Test of een website kwetsbaar is voor command injection — waarbij een aanvaller opdrachten kan uitvoeren op de server.",
  arjun: "Ontdekt verborgen parameters in website-URL's die mogelijk misbruikt kunnen worden.",
  skipfish: "Maakt een volledige kaart van een website en zoekt automatisch naar beveiligingsproblemen.",

  // Wireless
  "aireplay-ng": "Test de beveiliging van wifi-netwerken door netwerkverkeer te manipuleren en opnieuw te versturen.",
  reaver: "Probeert de WPS-pincode van wifi-routers te kraken om zo het wifi-wachtwoord te achterhalen.",
  wash: "Scant op wifi-netwerken die WPS (een snelle verbindmethode) ingeschakeld hebben, wat een beveiligingsrisico kan zijn.",
  kismet: "Luistert naar alle wifi-signalen in de buurt en brengt draadloze netwerken en apparaten in kaart.",

  // Sniffing & Spoofing
  tshark: "Vangt netwerkverkeer op en analyseert het — de commandoregel-versie van Wireshark.",
  tcpdump: "Basisgereedschap om netwerkverkeer op te vangen en te bekijken. Laat zien welke data er over het netwerk gaat.",
  bettercap: "Alles-in-één tool voor netwerkaanvallen: kan verkeer onderscheppen, wifi hacken en netwerken scannen.",
  responder: "Onderschept inloggegevens op een Windows-netwerk door zich voor te doen als een netwerkdienst.",
  arpspoof: "Vervalst netwerkberichten zodat verkeer van andere apparaten via jouw computer loopt. Wordt gebruikt om verkeer te onderscheppen.",
  ettercap: "Onderschept en analyseert netwerkverkeer tussen twee apparaten. Kan wachtwoorden en data 'afluisteren'.",
  macchanger: "Verandert het hardware-adres (MAC) van je netwerkkaart, zodat je apparaat niet herkend wordt op het netwerk.",

  // OSINT & Recon
  theharvester: "Verzamelt e-mailadressen, domeinnamen en andere publieke informatie over een bedrijf vanaf het internet.",
  amass: "Brengt alle subdomeinen van een website in kaart. Ontdekt verborgen diensten die mogelijk kwetsbaar zijn.",
  dnsrecon: "Onderzoekt DNS-instellingen van een domein en zoekt naar verkeerd geconfigureerde naamservers.",
  fierce: "Scant snel de DNS-configuratie van een domein om subdomeinen en IP-adressen te vinden.",
  spiderfoot: "Verzamelt automatisch alle publiek beschikbare informatie over een domein, persoon of bedrijf.",
  shodan: "Doorzoekt een database van alle apparaten die aan het internet hangen — van webcams tot servers.",
  "recon-ng": "Uitgebreid onderzoeksplatform dat informatie verzamelt uit openbare bronnen zoals sociale media en registers.",
  maltego: "Maakt visuele grafieken van verbanden tussen personen, domeinen, e-mails en bedrijven op basis van openbare bronnen.",

  // Exploitation
  searchsploit: "Doorzoekt een offline database van bekende kwetsbaarheden en exploits om te zien of een systeem vatbaar is.",
  impacket: "Set Python-tools om Windows-netwerken aan te vallen en te testen, zoals het uitlezen van wachtwoorden.",
  "evil-winrm": "Maakt verbinding met Windows-systemen via WinRM om te testen of ze op afstand overgenomen kunnen worden.",
  certipy: "Test de beveiliging van digitale certificaten in een Windows Active Directory-netwerk.",

  // Post-Exploitation
  "bloodhound-reader": "Analyseert de structuur van een Windows-netwerk en toont hoe een aanvaller van punt A naar B kan komen.",
  "linpeas-parser": "Analyseert de uitvoer van LinPEAS — een script dat zoekt naar manieren om hogere rechten te krijgen op Linux.",
  mimikatz: "Haalt wachtwoorden en inloggegevens uit het geheugen van Windows. Zeer krachtig voor beveiligingstests.",
  "winpeas-parser": "Analyseert de uitvoer van WinPEAS — een script dat zoekt naar manieren om hogere rechten te krijgen op Windows.",

  // Forensics
  volatility3: "Analyseert het werkgeheugen (RAM) van een computer om te zien welke programma's draaiden en wat er gebeurde.",
  binwalk: "Zoekt naar verborgen bestanden die ingebed zijn in andere bestanden, zoals firmware-images.",
  exiftool: "Leest verborgen metadata uit bestanden (wie het maakte, wanneer, met welk apparaat, locatie, etc.).",
  strings: "Haalt leesbare tekst uit bestanden — handig om te zien of er wachtwoorden of URLs verborgen zitten.",
  foremost: "Herstelt verwijderde bestanden uit een harde schijf of geheugenkaart op basis van bestandsformaten.",
  steghide: "Detecteert en haalt verborgen berichten uit afbeeldingen en audiobestanden (steganografie).",

  // Reverse Engineering
  radare2: "Analyseert programma's op hun laagste niveau (machinecode) om te begrijpen hoe ze werken.",
  objdump: "Toont de inhoud van gecompileerde programmabestanden — handig om te zien wat een programma precies doet.",
  strace: "Volgt alle systeemoproepen die een programma doet — laat zien welke bestanden en netwerkverbindingen het gebruikt.",
  ghidra: "Krachtige tool (van de NSA) die gecompileerde programma's omzet naar leesbare code voor analyse.",
  pwntools: "Python-bibliotheek voor het schrijven en testen van exploits, vooral voor beveiligingsonderzoek.",
  ropper: "Vindt bruikbare code-fragmenten in programma's die misbruikt kunnen worden voor geheugen-aanvallen.",

  // Vulnerability Analysis
  lynis: "Controleert Linux/Unix-systemen op beveiligingsinstellingen en geeft advies om deze te verbeteren.",
  trivy: "Scant Docker-containers en code-afhankelijkheden op bekende kwetsbaarheden.",
  grype: "Zoekt in softwarepakketten naar bekende beveiligingslekken en geeft een overzicht van risico's.",
  chkrootkit: "Controleert of er kwaadaardige software (rootkits) verborgen zit op een Linux-systeem.",
  openvas: "Uitgebreide kwetsbaarheidsscanner die duizenden beveiligingschecks uitvoert op netwerken en systemen.",

  // Cryptography
  hashid: "Herkent het type versleuteling (hash) dat gebruikt is om een wachtwoord te beveiligen.",
  hash_identifier: "Vergelijkbaar met hashID: identificeert welk type versleuteling gebruikt is voor een hash.",
  cyberchef: "Online 'Zwitsers zakmes' voor versleuteling, decodering en data-analyse — alles in één tool.",
  stegseek: "Zoekt razendsnel naar verborgen berichten in afbeeldingen die met steganografie zijn verstopt.",
  featherduster: "Analyseert versleutelde berichten automatisch om de gebruikte versleutelmethode te achterhalen.",
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

export default function ToolsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set());
  const [target, setTarget] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null);

  const { data: toolsData, isLoading: toolsLoading } = useQuery({
    queryKey: ["tools-available"],
    queryFn: () => toolsApi.available().then((r) => r.data as Record<string, ToolInfo>),
  });

  const { data: profilesData } = useQuery({
    queryKey: ["tools-profiles"],
    queryFn: () => toolsApi.profiles().then((r) => r.data as Record<string, string[]>),
  });

  const startScanMutation = useMutation({
    mutationFn: (data: { target: string; tools?: string[]; profile?: string }) =>
      toolsApi.startScan(data),
    onSuccess: (res) => {
      alert(`Tool scan gestart! Scan ID: ${res.data.scan_id}`);
    },
  });

  const tools = toolsData ? Object.values(toolsData) : [];

  // Group by category
  const categories = new Map<string, ToolInfo[]>();
  tools.forEach((tool) => {
    const cat = tool.category;
    if (!categories.has(cat)) categories.set(cat, []);
    categories.get(cat)!.push(tool);
  });

  // Filter
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
    if (selectedTools.size > 0) {
      startScanMutation.mutate({
        target: target.trim(),
        tools: Array.from(selectedTools),
      });
    } else if (selectedProfile) {
      startScanMutation.mutate({
        target: target.trim(),
        profile: selectedProfile,
      });
    }
  };

  const availableCount = tools.filter((t) => t.available).length;
  const totalCount = tools.length;

  if (toolsLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Tools laden...</span>
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
        <div className="flex items-center gap-3">
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
      </div>

      {/* Quick Scan Bar */}
      <div className="rounded-xl border bg-card p-5 shadow-sm">
        <h2 className="text-lg font-semibold mb-3">Tool Scan Starten</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="Target (bijv. example.com of 192.168.1.0/24)"
            className="flex-1 rounded-lg border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
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
            Scan ({selectedTools.size} tools)
          </button>
        </div>

        {/* Profiles */}
        {profilesData && (
          <div className="mt-3 flex flex-wrap gap-2">
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

      {/* Search & Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Zoek tools..."
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
            Alle
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

      {/* Tools Grid by Category */}
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
                  ({catTools.filter((t) => t.available).length}/{catTools.length})
                </span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {catTools.map((tool) => (
                  <div
                    key={tool.name}
                    onClick={() => tool.available && toggleTool(tool.name)}
                    className={`relative rounded-xl border p-4 transition-all cursor-pointer ${
                      selectedTools.has(tool.name)
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : tool.available
                        ? "border-border bg-card hover:border-primary/50 hover:shadow-sm"
                        : "border-border bg-muted/30 opacity-60 cursor-not-allowed"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium text-sm">{tool.display_name}</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">{tool.name}</p>
                      </div>
                      {tool.available ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                      )}
                    </div>
                    {TOOL_DESCRIPTIONS[tool.name] && (
                      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
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
