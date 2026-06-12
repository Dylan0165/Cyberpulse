#!/bin/bash
# ============================================================
# AutoPentest AI — Tool Installer voor Ubuntu 22.04 / 24.04
# Installeert alle pentesttools van https://www.kali.org/tools/all-tools/
# Gebruik: sudo bash install-tools.sh
# ============================================================

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[-]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then
  err "Draai dit script als root: sudo bash install-tools.sh"
  exit 1
fi

log "Systeem updaten..."
apt update && apt upgrade -y
apt install -y software-properties-common curl wget git unzip tar build-essential \
  python3 python3-pip python3-venv python3-dev ruby ruby-dev perl libssl-dev \
  libffi-dev libpcap-dev libxml2-dev libxslt1-dev zlib1g-dev libjpeg-dev \
  gcc g++ make cmake pkg-config net-tools dnsutils whois netcat-openbsd \
  tcpdump wireshark-common tshark aircrack-ng

# ============================================================
# 1. RECONNAISSANCE & OSINT
# ============================================================
log "Installeren: Reconnaissance & OSINT tools..."
apt install -y \
  nmap masscan \
  recon-ng maltego \
  theharvester \
  dnsrecon dnsenum dnsmap \
  whois \
  whatweb wafw00f \
  sslscan sslyze \
  enum4linux smbclient \
  snmp snmpcheck \
  nbtscan \
  netdiscover arp-scan \
  fping hping3 \
  traceroute \
  p0f \
  dmitry \
  onesixtyone \
  smtp-user-enum \
  fierce \
  dnstracer

# ============================================================
# 2. WEB APPLICATION TESTING
# ============================================================
log "Installeren: Web application tools..."
apt install -y \
  nikto \
  dirb dirbuster \
  wfuzz \
  sqlmap \
  xsser \
  commix \
  wapiti \
  skipfish \
  w3af \
  webscarab \
  zaproxy \
  curl wget \
  gobuster \
  arjun

# ============================================================
# 3. NETWORK SERVICES
# ============================================================
log "Installeren: Network service tools..."
apt install -y \
  ncat \
  socat \
  netcat-openbsd \
  tcpdump \
  wireshark-common tshark \
  ettercap-text-only \
  arpspoof \
  dsniff \
  sslstrip \
  bettercap \
  macchanger \
  responder \
  impacket-scripts \
  enum4linux \
  nbtscan \
  onesixtyone \
  snmpcheck

# ============================================================
# 4. PASSWORD ATTACKS & BRUTE FORCE
# ============================================================
log "Installeren: Password attack tools..."
apt install -y \
  hydra hydra-gtk \
  medusa \
  john \
  hashcat \
  ophcrack \
  crunch \
  wordlists \
  cewl \
  fcrackzip \
  pdfcrack \
  samdump2 \
  chntpw \
  patator

# ============================================================
# 5. EXPLOITATION FRAMEWORKS
# ============================================================
log "Installeren: Exploitation frameworks..."
apt install -y \
  metasploit-framework \
  exploitdb \
  armitage \
  beef-xss \
  set

# ============================================================
# 6. POST-EXPLOITATION
# ============================================================
log "Installeren: Post-exploitation tools..."
apt install -y \
  netcat-openbsd \
  socat \
  weevely \
  laudanum \
  webshells \
  mimikatz \
  powersploit \
  empire

# ============================================================
# 7. WIRELESS
# ============================================================
log "Installeren: Wireless tools..."
apt install -y \
  aircrack-ng \
  airgeddon \
  wifite \
  reaver \
  bully \
  pixiewps \
  kismet \
  cowpatty \
  mdk3 mdk4 \
  hostapd \
  dnsmasq

# ============================================================
# 8. FORENSICS & REVERSE ENGINEERING
# ============================================================
log "Installeren: Forensics tools..."
apt install -y \
  binwalk \
  foremost \
  scalpel \
  autopsy \
  volatility3 \
  strings \
  ltrace strace \
  gdb \
  radare2 \
  ghidra \
  objdump \
  hexedit \
  xxd \
  dc3dd \
  ddrescue \
  sleuthkit \
  bulk-extractor \
  exiftool \
  steghide \
  stegsnow

# ============================================================
# 9. SSL/TLS & CRYPTOGRAFIE
# ============================================================
log "Installeren: SSL/TLS tools..."
apt install -y \
  sslscan \
  sslyze \
  openssl \
  testssl.sh \
  gnutls-bin

# ============================================================
# 10. VULNERABILITY SCANNERS
# ============================================================
log "Installeren: Vulnerability scanners..."
apt install -y \
  openvas \
  lynis \
  chkrootkit \
  rkhunter \
  tiger \
  nessus 2>/dev/null || warn "Nessus moet handmatig geïnstalleerd worden van tenable.com"

# ============================================================
# GO INSTALLEREN (voor moderne tools)
# ============================================================
log "Go installeren..."
if ! command -v go &>/dev/null; then
  GO_VERSION="1.22.0"
  wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
  rm -rf /usr/local/go
  tar -C /usr/local -xzf /tmp/go.tar.gz
  echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> /etc/profile.d/go.sh
  export PATH=$PATH:/usr/local/go/bin
  log "Go ${GO_VERSION} geïnstalleerd"
fi
source /etc/profile.d/go.sh 2>/dev/null || export PATH=$PATH:/usr/local/go/bin

# ============================================================
# GO-BASED TOOLS
# ============================================================
log "Installeren: Go-based tools..."
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null && log "nuclei OK" || warn "nuclei mislukt"
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>/dev/null && log "subfinder OK" || warn "subfinder mislukt"
go install github.com/projectdiscovery/httpx/cmd/httpx@latest 2>/dev/null && log "httpx OK" || warn "httpx mislukt"
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest 2>/dev/null && log "naabu OK" || warn "naabu mislukt"
go install github.com/projectdiscovery/katana/cmd/katana@latest 2>/dev/null && log "katana OK" || warn "katana mislukt"
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest 2>/dev/null && log "dnsx OK" || warn "dnsx mislukt"
go install github.com/ffuf/ffuf/v2@latest 2>/dev/null && log "ffuf OK" || warn "ffuf mislukt"
go install github.com/OJ/gobuster/v3@latest 2>/dev/null && log "gobuster OK" || warn "gobuster mislukt"
go install github.com/tomnomnom/waybackurls@latest 2>/dev/null && log "waybackurls OK" || warn "waybackurls mislukt"
go install github.com/tomnomnom/assetfinder@latest 2>/dev/null && log "assetfinder OK" || warn "assetfinder mislukt"
go install github.com/tomnomnom/httprobe@latest 2>/dev/null && log "httprobe OK" || warn "httprobe mislukt"
go install github.com/hakluke/hakrawler@latest 2>/dev/null && log "hakrawler OK" || warn "hakrawler mislukt"
go install github.com/lc/gau/v2/cmd/gau@latest 2>/dev/null && log "gau OK" || warn "gau mislukt"

# Binaries beschikbaar maken voor alle gebruikers
cp ~/go/bin/* /usr/local/bin/ 2>/dev/null || true

# ============================================================
# PYTHON-BASED TOOLS
# ============================================================
log "Installeren: Python-based tools..."
pip3 install --break-system-packages \
  theHarvester \
  impacket \
  pwntools \
  scapy \
  requests \
  beautifulsoup4 \
  shodan \
  censys \
  dnstwist \
  arjun \
  paramspider \
  jwt_tool \
  ysoserial \
  crackmapexec \
  evil-winrm \
  certipy-ad \
  bloodhound \
  ldapdomaindump \
  pypykatz \
  volatility3 \
  semgrep \
  truffleHog \
  gitleaks 2>/dev/null || true

# ============================================================
# RUBY-BASED TOOLS
# ============================================================
log "Installeren: Ruby-based tools..."
gem install \
  wpscan \
  evil-winrm 2>/dev/null || warn "Sommige Ruby gems zijn mislukt"

# ============================================================
# WORDLISTS
# ============================================================
log "Installeren: Wordlists..."
apt install -y wordlists 2>/dev/null || true
if [ ! -f /usr/share/wordlists/rockyou.txt ]; then
  if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then
    gunzip /usr/share/wordlists/rockyou.txt.gz
    log "rockyou.txt uitgepakt"
  fi
fi

# SecLists installeren
if [ ! -d /usr/share/seclists ]; then
  log "SecLists downloaden..."
  git clone --depth 1 https://github.com/danielmiessler/SecLists /usr/share/seclists
  log "SecLists geïnstalleerd in /usr/share/seclists"
fi

# ============================================================
# METASPLOIT APART (als niet via apt)
# ============================================================
if ! command -v msfconsole &>/dev/null; then
  log "Metasploit installeren via installer script..."
  curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall
  chmod 755 /tmp/msfinstall
  /tmp/msfinstall
fi

# ============================================================
# GITLEAKS (secrets scanner)
# ============================================================
log "Gitleaks installeren..."
GITLEAKS_VERSION="8.18.2"
wget -q "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" -O /tmp/gitleaks.tar.gz
tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks 2>/dev/null && log "Gitleaks OK" || warn "Gitleaks mislukt"

# ============================================================
# TESTSSL.SH
# ============================================================
log "testssl.sh installeren..."
if ! command -v testssl.sh &>/dev/null; then
  git clone --depth 1 https://github.com/drwetter/testssl.sh /opt/testssl
  ln -sf /opt/testssl/testssl.sh /usr/local/bin/testssl.sh
  log "testssl.sh geïnstalleerd"
fi

# ============================================================
# NUCLEI TEMPLATES DOWNLOADEN
# ============================================================
log "Nuclei templates downloaden..."
nuclei -update-templates 2>/dev/null || true

# ============================================================
# KLAAR
# ============================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Installatie voltooid!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Geïnstalleerde tools (check):"
for tool in nmap masscan nikto sqlmap hydra john hashcat aircrack-ng \
            nuclei subfinder httpx ffuf gobuster gitleaks testssl.sh \
            metasploit-framework binwalk foremost radare2 wpscan; do
  if command -v "$tool" &>/dev/null 2>&1 || dpkg -l "$tool" &>/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $tool"
  else
    echo -e "  ${RED}✗${NC} $tool (niet gevonden)"
  fi
done

echo ""
echo "Wordlists locatie: /usr/share/wordlists/"
echo "SecLists locatie:  /usr/share/seclists/"
echo "Nuclei templates:  ~/.local/nuclei-templates/"
echo ""
warn "Herstart de terminal om PATH-wijzigingen te activeren: source /etc/profile.d/go.sh"
