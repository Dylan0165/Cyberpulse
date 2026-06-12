#!/bin/bash
# ============================================================
# AutoPentest AI — Volledig 600+ Tools Installer
# Installeert ALLE Kali Linux tools op Ubuntu 22.04 / 24.04
# via de officiële Kali repository + extra bronnen
#
# Gebruik: sudo bash install-all-tools.sh
# Benodigde ruimte: ~60-80 GB
# Tijdsduur: 45-90 minuten
# ============================================================

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log()     { echo -e "${GREEN}[+]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
err()     { echo -e "${RED}[-]${NC} $1"; }
section() { echo -e "\n${BLUE}[===]${NC} $1\n"; }

if [ "$EUID" -ne 0 ]; then
  err "Draai dit script als root: sudo bash install-all-tools.sh"
  exit 1
fi

section "FASE 1 — Systeem voorbereiden"

apt update && apt upgrade -y
apt install -y \
  curl wget git unzip tar nano vim \
  build-essential cmake pkg-config \
  python3 python3-pip python3-venv python3-dev \
  ruby ruby-dev rubygems \
  perl libssl-dev libffi-dev \
  libpcap-dev libxml2-dev libxslt1-dev \
  zlib1g-dev libjpeg-dev libpng-dev \
  gcc g++ make \
  net-tools iproute2 \
  software-properties-common \
  gnupg2 lsb-release \
  apt-transport-https ca-certificates

# ============================================================
# FASE 2 — Kali Linux repository toevoegen met pinning
# Dit geeft toegang tot alle 600+ Kali tools via apt
# Package pinning zorgt dat Ubuntu pakketten NIET worden
# overschreven door Kali versies
# ============================================================
section "FASE 2 — Kali Linux repository toevoegen"

log "Kali GPG sleutel toevoegen..."
wget -q -O /tmp/kali-key.asc https://archive.kali.org/archive-key.asc
gpg --dearmor < /tmp/kali-key.asc > /etc/apt/trusted.gpg.d/kali-archive-keyring.gpg
log "Kali repository toevoegen..."
echo "deb http://http.kali.org/kali kali-rolling main contrib non-free non-free-firmware" \
  > /etc/apt/sources.list.d/kali.list

log "Package pinning instellen (voorkomt Ubuntu conflicts)..."
cat > /etc/apt/preferences.d/kali-pin << 'EOF'
# Kali pakketten krijgen lage prioriteit — Ubuntu pakketten winnen altijd
Package: *
Pin: release o=Kali
Pin-Priority: 100

# Uitzondering: pentest tools die ALLEEN in Kali zitten
Package: kali-linux-everything
Pin: release o=Kali
Pin-Priority: 500

Package: kali-linux-large
Pin: release o=Kali
Pin-Priority: 500
EOF

apt update

# ============================================================
# FASE 3 — Kali metapakketten installeren
# kali-linux-everything = alle 600+ tools in één pakket
# ============================================================
section "FASE 3 — Alle Kali tools installeren (dit duurt 45-90 min)"

warn "Nu worden alle 600+ tools gedownload en geïnstalleerd..."
warn "Zorg voor stabiele internetverbinding en voldoende schijfruimte (60+ GB)"
echo ""

# Probeer kali-linux-everything (alles)
if apt install -y kali-linux-everything 2>/dev/null; then
  log "kali-linux-everything succesvol geïnstalleerd!"
else
  warn "kali-linux-everything mislukt, installeren per categorie..."

  # Information Gathering
  section "Information Gathering tools..."
  apt install -y \
    nmap masscan unicornscan \
    recon-ng maltego \
    theharvester \
    dnsenum dnsrecon dnsmap dnstracer dnstwist \
    whois \
    whatweb wafw00f \
    sslscan sslyze \
    enum4linux enum4linux-ng \
    smbclient smbmap \
    snmp snmpcheck \
    nbtscan \
    netdiscover arp-scan \
    fping hping3 \
    p0f \
    dmitry \
    onesixtyone \
    smtp-user-enum \
    fierce \
    sublist3r \
    amass \
    shodan \
    spiderfoot \
    maltego \
    osrframework \
    metagoofil \
    instaloader \
    sherlock \
    phoneinfoga \
    holehe \
    finalrecon \
    raccoon-scanner \
    photon \
    carbon14 \
    sn0int \
    reconftw 2>/dev/null || true

  # Vulnerability Analysis
  section "Vulnerability Analysis tools..."
  apt install -y \
    nikto \
    openvas gvm \
    lynis \
    nessus 2>/dev/null || true
  apt install -y \
    legion \
    sparrow-wifi \
    yersinia \
    ike-scan \
    cisco-auditing-tool \
    cisco-global-exploiter \
    cisco-ocs \
    cisco-torch \
    copy-router-config \
    nmap \
    pocsuite3 \
    unix-privesc-check \
    bed \
    doona \
    sfuzz \
    powerfuzzer \
    siparmyknife \
    voiphopper 2>/dev/null || true

  # Web Application Analysis
  section "Web Application tools..."
  apt install -y \
    burpsuite \
    zaproxy \
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
    paros \
    vega \
    arachni \
    golismero \
    grabber \
    fierce \
    cutycapt \
    httprint \
    httrack \
    parsero \
    wpscan \
    joomscan \
    droopescan \
    clusterd \
    cmseek \
    blindelephant \
    plecost \
    wig \
    whatweb \
    wafw00f \
    wuzz \
    hakrawler \
    gospider \
    photon \
    paramspider \
    arjun \
    kiterunner \
    dalfox \
    ghauri 2>/dev/null || true

  # Database Assessment
  section "Database Assessment tools..."
  apt install -y \
    sqlmap \
    bbqsql \
    hexorbase \
    jsql-injection \
    mdbtools \
    oscanner \
    sidguesser \
    sipcrack \
    tnscmd10g \
    oracle-instantclient \
    pgexploit \
    mongoaudit 2>/dev/null || true

  # Password Attacks
  section "Password Attack tools..."
  apt install -y \
    hydra hydra-gtk \
    medusa \
    john \
    johnny \
    hashcat \
    hashcat-utils \
    hash-identifier \
    ophcrack ophcrack-cli \
    crunch \
    wordlists \
    cewl \
    rsmangler \
    fcrackzip \
    pdfcrack \
    samdump2 \
    chntpw \
    patator \
    crowbar \
    thc-pptp-bruter \
    onesixtyone \
    sucrack \
    pack \
    pipal \
    brutespray \
    sprayhound \
    kerbrute \
    username-anarchy 2>/dev/null || true

  # Wireless Attacks
  section "Wireless tools..."
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
    hostapd-wpe \
    dnsmasq \
    freeradius-wpe \
    iw wireless-tools \
    wifi-honey \
    pyrit \
    eapmd5pass \
    asleap \
    coWPAtty \
    giskismet \
    kalibrate-rtl \
    rfkill \
    bluelog \
    blueranger \
    bluesnarfer \
    bluez bluez-tools \
    btscanner \
    crackle \
    spooftooph \
    wireshark tshark \
    horst \
    wavemon 2>/dev/null || true

  # Reverse Engineering
  section "Reverse Engineering tools..."
  apt install -y \
    radare2 \
    ghidra \
    gdb gdb-multiarch \
    peda \
    pwndbg \
    binwalk \
    ltrace strace \
    nasm \
    yasm \
    objdump \
    hexedit \
    xxd \
    edb-debugger \
    apktool \
    dex2jar \
    jd-gui \
    jadx \
    android-tools-adb \
    smali \
    bytecode-viewer \
    simplify \
    cfr \
    procyon \
    krakatau \
    recaf \
    javasnoop \
    floss \
    cutter \
    rizin \
    iaito \
    unicorn \
    keystone-engine \
    capstone \
    r2ghidra \
    frida-tools \
    objection 2>/dev/null || true

  # Exploitation Tools
  section "Exploitation tools..."
  apt install -y \
    metasploit-framework \
    armitage \
    beef-xss \
    set \
    thefatrat \
    venom \
    unicorn \
    empire \
    covenant \
    koadic \
    merlin-server \
    crackmapexec \
    impacket-scripts \
    responder \
    evil-winrm \
    smbexec \
    powersploit \
    nishang \
    shellter \
    veil \
    msfpc \
    routersploit \
    exploitdb searchsploit \
    gdb-peda \
    pwntools \
    checksec \
    one_gadget \
    ropper \
    ropgadget \
    libseccomp-dev \
    patchelf 2>/dev/null || true

  # Sniffing & Spoofing
  section "Sniffing & Spoofing tools..."
  apt install -y \
    wireshark tshark \
    tcpdump \
    ettercap-text-only ettercap-graphical \
    arpspoof \
    dsniff \
    sslstrip \
    bettercap \
    macchanger \
    netsniff-ng \
    darkstat \
    driftnet \
    urlsnarf \
    webspy \
    msgsnarf \
    filesnarf \
    mailsnarf \
    tcpflow \
    tcpreplay \
    tcpslice \
    p0f \
    ngrep \
    dnschef \
    sslsplit \
    mitmproxy \
    zaproxy \
    burpsuite \
    hetty \
    intercepter-ng \
    hamster-sidejack \
    ferret-sidejack 2>/dev/null || true

  # Post Exploitation
  section "Post Exploitation tools..."
  apt install -y \
    metasploit-framework \
    empire \
    crackmapexec \
    impacket-scripts \
    mimikatz \
    evil-winrm \
    bloodhound \
    neo4j \
    sharphound \
    powerview \
    powerupsql \
    rubeus \
    certify \
    kekeo \
    pypykatz \
    secretsdump \
    lsassy \
    procdump \
    volatility3 \
    weevely \
    laudanum \
    webshells \
    laudanum \
    ncat \
    socat \
    chisel \
    ligolo-ng \
    plink \
    proxychains4 \
    redsocks \
    iodine \
    dns2tcp \
    ptunnel-ng \
    sshuttle \
    venom \
    msfvenom 2>/dev/null || true

  # Digital Forensics
  section "Digital Forensics tools..."
  apt install -y \
    autopsy \
    sleuthkit \
    volatility3 \
    binwalk \
    foremost \
    scalpel \
    bulk-extractor \
    dc3dd \
    dcfldd \
    ddrescue \
    gddrescue \
    testdisk \
    photorec \
    exiftool \
    hexedit \
    strings \
    pdfinfo \
    pdfimages \
    pdftk \
    pst-utils \
    readpst \
    libpff-utils \
    libesedb-utils \
    libmsiecf-utils \
    libregf-utils \
    liblnk-utils \
    libevt-utils \
    libevtx-utils \
    libscca-utils \
    libfvde-utils \
    libvhdi-utils \
    libvmdk-utils \
    libewf-dev ewf-tools \
    afftools \
    guymager \
    android-sdk-libsparse-utils \
    chkrootkit \
    rkhunter \
    unhide \
    lynis \
    tiger \
    aide \
    tripwire 2>/dev/null || true

  # Steganography
  section "Steganography tools..."
  apt install -y \
    steghide \
    stegsnow \
    stegosuite \
    outguess \
    openstego \
    gimp \
    exiv2 \
    exiftool \
    pngtools \
    identify \
    zsteg \
    stegcracker \
    stegseek 2>/dev/null || true

  # Reporting
  section "Reporting tools..."
  apt install -y \
    dradis \
    piperka \
    magictree \
    cutycapt \
    recordmydesktop \
    faraday 2>/dev/null || true

  # Social Engineering
  section "Social Engineering tools..."
  apt install -y \
    set \
    gophish \
    evilginx2 \
    beef-xss \
    maltego \
    creepy \
    urlcrazy 2>/dev/null || true

fi

# ============================================================
# FASE 4 — Go installeren
# ============================================================
section "FASE 4 — Go installeren"

if ! command -v go &>/dev/null; then
  GO_VERSION="1.22.3"
  log "Go ${GO_VERSION} downloaden..."
  wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
  rm -rf /usr/local/go
  tar -C /usr/local -xzf /tmp/go.tar.gz
  echo 'export PATH=$PATH:/usr/local/go/bin:/root/go/bin' >> /etc/profile.d/go.sh
  echo 'export PATH=$PATH:/usr/local/go/bin:/root/go/bin' >> /root/.bashrc
  export PATH=$PATH:/usr/local/go/bin
  log "Go ${GO_VERSION} geïnstalleerd"
else
  log "Go al geïnstalleerd: $(go version)"
fi
export PATH=$PATH:/usr/local/go/bin:/root/go/bin

# ============================================================
# FASE 5 — Go-based tools (moderne security tools)
# ============================================================
section "FASE 5 — Go-based tools installeren"

GO_TOOLS=(
  "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
  "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
  "github.com/projectdiscovery/httpx/cmd/httpx@latest"
  "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
  "github.com/projectdiscovery/katana/cmd/katana@latest"
  "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
  "github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest"
  "github.com/projectdiscovery/mapcidr/cmd/mapcidr@latest"
  "github.com/projectdiscovery/notify/cmd/notify@latest"
  "github.com/projectdiscovery/proxify/cmd/proxify@latest"
  "github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest"
  "github.com/projectdiscovery/tlsx/cmd/tlsx@latest"
  "github.com/projectdiscovery/uncover/cmd/uncover@latest"
  "github.com/ffuf/ffuf/v2@latest"
  "github.com/OJ/gobuster/v3@latest"
  "github.com/tomnomnom/waybackurls@latest"
  "github.com/tomnomnom/assetfinder@latest"
  "github.com/tomnomnom/httprobe@latest"
  "github.com/tomnomnom/gf@latest"
  "github.com/tomnomnom/anew@latest"
  "github.com/tomnomnom/unfurl@latest"
  "github.com/tomnomnom/qsreplace@latest"
  "github.com/hakluke/hakrawler@latest"
  "github.com/lc/gau/v2/cmd/gau@latest"
  "github.com/lc/subjs@latest"
  "github.com/jaeles-project/gospider@latest"
  "github.com/hahwul/dalfox/v2@latest"
  "github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest"
  "github.com/d3mondev/puredns/v2@latest"
  "github.com/owasp-amass/amass/v4/...@master"
  "github.com/projectdiscovery/asnmap/cmd/asnmap@latest"
  "github.com/ferreiraklet/Jeeves@latest"
  "github.com/phor3nsic/favicon_hash_shodan@latest"
  "github.com/glebarez/cero@latest"
  "github.com/trickest/dsieve@latest"
  "github.com/trickest/enumerepo@latest"
  "github.com/trickest/trieharder@latest"
  "github.com/trufflesecurity/trufflehog/v3@latest"
  "github.com/gitleaks/gitleaks/v8@latest"
  "github.com/insidersec/insider@latest"
  "github.com/chvancooten/NimPackt-v1@latest"
  "github.com/sensepost/gowitness@latest"
  "github.com/michenriksen/aquatone@latest"
  "github.com/bp0lr/dmut@latest"
  "github.com/takshal/freq@latest"
  "github.com/cemulus/crt@latest"
  "github.com/musana/mx-takeover@latest"
  "github.com/edoardottt/scilla/cmd/scilla@latest"
  "github.com/Ice3man543/hawkrawler@latest"
  "github.com/Cgboal/SonarSearch/cmd/sonar@latest"
  "github.com/channyein1337/jsleak@latest"
  "github.com/m3n0sd0n4ld/GooFuzz@latest"
)

for tool in "${GO_TOOLS[@]}"; do
  name=$(basename "${tool%%@*}")
  log "Installeren: $name"
  go install "$tool" 2>/dev/null && log "  ✓ $name" || warn "  ✗ $name mislukt"
done

# Binaries beschikbaar maken
cp /root/go/bin/* /usr/local/bin/ 2>/dev/null || true

# ============================================================
# FASE 6 — Python-based tools
# ============================================================
section "FASE 6 — Python-based tools installeren"

pip3 install --break-system-packages \
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
  crackmapexec \
  pypykatz \
  volatility3 \
  semgrep \
  truffleHog \
  wafw00f \
  wapiti3 \
  sslyze \
  testssl \
  cloudsploit \
  pacu \
  ScoutSuite \
  prowler \
  detect-secrets \
  bandit \
  safety \
  pylint \
  black \
  mitm6 \
  ldapdomaindump \
  bloodhound \
  certipy-ad \
  coercer \
  netexec \
  lsassy \
  sprayhound \
  kerbrute \
  pkinittools \
  dploot \
  manspider \
  targetedKerberoast \
  donpapi \
  hekatomb \
  neo4j \
  stegcracker \
  stegseek \
  binwalk \
  frida-tools \
  objection \
  androguard \
  apkid \
  mobsf \
  drozer \
  apkleaks \
  fridump \
  r2pipe \
  pycparser \
  angr \
  z3-solver \
  unicorn \
  keystone-engine \
  capstone \
  ropper \
  ropgadget \
  one-gadget 2>/dev/null || true

# ============================================================
# FASE 7 — Ruby-based tools
# ============================================================
section "FASE 7 — Ruby-based tools installeren"

gem install \
  wpscan \
  evil-winrm \
  winrm \
  winrm-fs \
  stringio 2>/dev/null || warn "Sommige gems zijn mislukt"

# ============================================================
# FASE 8 — Specifieke tools handmatig installeren
# ============================================================
section "FASE 8 — Handmatige tool installaties"

# Gitleaks
log "Gitleaks installeren..."
GITLEAKS_VER="8.18.2"
wget -q "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VER}/gitleaks_${GITLEAKS_VER}_linux_x64.tar.gz" \
  -O /tmp/gitleaks.tar.gz
tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks 2>/dev/null && log "Gitleaks OK" || warn "Gitleaks mislukt"

# testssl.sh
log "testssl.sh installeren..."
if ! command -v testssl.sh &>/dev/null; then
  git clone --depth 1 https://github.com/drwetter/testssl.sh /opt/testssl
  ln -sf /opt/testssl/testssl.sh /usr/local/bin/testssl.sh
fi

# Chisel (tunneling)
log "Chisel installeren..."
CHISEL_VER="1.9.1"
wget -q "https://github.com/jpillora/chisel/releases/download/v${CHISEL_VER}/chisel_${CHISEL_VER}_linux_amd64.gz" \
  -O /tmp/chisel.gz
gunzip -f /tmp/chisel.gz && mv /tmp/chisel /usr/local/bin/chisel && chmod +x /usr/local/bin/chisel \
  && log "Chisel OK" || warn "Chisel mislukt"

# Ligolo-ng (tunneling)
log "Ligolo-ng installeren..."
wget -q "https://github.com/nicocha30/ligolo-ng/releases/latest/download/ligolo-ng_agent_linux_amd64" \
  -O /usr/local/bin/ligolo-agent && chmod +x /usr/local/bin/ligolo-agent \
  && log "Ligolo-ng agent OK" || warn "Ligolo-ng mislukt"

# Rustscan (snelle poortscan)
log "Rustscan installeren..."
wget -q "https://github.com/RustScan/RustScan/releases/latest/download/rustscan_2.1.1_amd64.deb" \
  -O /tmp/rustscan.deb
dpkg -i /tmp/rustscan.deb 2>/dev/null && log "Rustscan OK" || warn "Rustscan mislukt"

# Feroxbuster (web fuzzer)
log "Feroxbuster installeren..."
wget -q "https://github.com/epi052/feroxbuster/releases/latest/download/x86_64-linux-feroxbuster.zip" \
  -O /tmp/ferox.zip
unzip -o /tmp/ferox.zip -d /usr/local/bin feroxbuster 2>/dev/null \
  && chmod +x /usr/local/bin/feroxbuster \
  && log "Feroxbuster OK" || warn "Feroxbuster mislukt"

# Kerbrute
log "Kerbrute installeren..."
wget -q "https://github.com/ropnop/kerbrute/releases/latest/download/kerbrute_linux_amd64" \
  -O /usr/local/bin/kerbrute && chmod +x /usr/local/bin/kerbrute \
  && log "Kerbrute OK" || warn "Kerbrute mislukt"

# CrackMapExec / NetExec
log "NetExec installeren..."
pip3 install --break-system-packages netexec 2>/dev/null && log "NetExec OK" || warn "NetExec mislukt"

# Enum4linux-ng
log "Enum4linux-ng installeren..."
git clone --depth 1 https://github.com/cddmp/enum4linux-ng /opt/enum4linux-ng 2>/dev/null
ln -sf /opt/enum4linux-ng/enum4linux-ng.py /usr/local/bin/enum4linux-ng 2>/dev/null

# Impacket scripts apart
log "Impacket scripts installeren..."
pip3 install --break-system-packages impacket 2>/dev/null \
  && log "Impacket OK" || warn "Impacket mislukt"

# LinPEAS / WinPEAS
log "PEASS-ng downloaden..."
mkdir -p /opt/PEASS
wget -q "https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh" \
  -O /opt/PEASS/linpeas.sh && chmod +x /opt/PEASS/linpeas.sh \
  && log "LinPEAS OK" || warn "LinPEAS mislukt"
wget -q "https://github.com/peass-ng/PEASS-ng/releases/latest/download/winPEASx64.exe" \
  -O /opt/PEASS/winPEASx64.exe \
  && log "WinPEAS OK" || warn "WinPEAS mislukt"

# LinEnum
log "LinEnum downloaden..."
wget -q "https://raw.githubusercontent.com/rebootuser/LinEnum/master/LinEnum.sh" \
  -O /opt/PEASS/LinEnum.sh && chmod +x /opt/PEASS/LinEnum.sh

# Metasploit (als niet via Kali repo)
if ! command -v msfconsole &>/dev/null; then
  log "Metasploit installeren via official installer..."
  curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall
  chmod 755 /tmp/msfinstall && /tmp/msfinstall \
    && log "Metasploit OK" || warn "Metasploit mislukt"
fi

# ============================================================
# FASE 9 — Wordlists & Nuclei templates
# ============================================================
section "FASE 9 — Wordlists & templates"

# rockyou.txt uitpakken
if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then
  gunzip -f /usr/share/wordlists/rockyou.txt.gz && log "rockyou.txt uitgepakt"
fi

# SecLists (grootste wordlist collectie)
if [ ! -d /usr/share/seclists ]; then
  log "SecLists downloaden (~1 GB)..."
  git clone --depth 1 https://github.com/danielmiessler/SecLists /usr/share/seclists \
    && log "SecLists OK"
fi

# Nuclei templates
log "Nuclei templates bijwerken..."
nuclei -update-templates 2>/dev/null && log "Nuclei templates OK" || warn "Nuclei templates mislukt"

# PayloadsAllTheThings
if [ ! -d /opt/PayloadsAllTheThings ]; then
  log "PayloadsAllTheThings downloaden..."
  git clone --depth 1 https://github.com/swisskyrepo/PayloadsAllTheThings /opt/PayloadsAllTheThings \
    && log "PayloadsAllTheThings OK"
fi

# ============================================================
# FASE 10 — PATH instellen
# ============================================================
section "FASE 10 — PATH configureren"

cat >> /etc/profile.d/pentest-tools.sh << 'EOF'
export PATH=$PATH:/usr/local/go/bin:/root/go/bin:/opt/testssl
export WORDLISTS=/usr/share/wordlists
export SECLISTS=/usr/share/seclists
export PEASS=/opt/PEASS
EOF

chmod +x /etc/profile.d/pentest-tools.sh

# ============================================================
# SAMENVATTING
# ============================================================
section "INSTALLATIE VOLTOOID"

echo -e "${GREEN}Tool check:${NC}"
TOOLS=(
  nmap masscan rustscan nikto sqlmap hydra john hashcat
  aircrack-ng metasploit-framework burpsuite zaproxy
  nuclei subfinder httpx ffuf gobuster feroxbuster
  gitleaks testssl.sh chisel kerbrute
  wireshark tshark tcpdump
  binwalk foremost strings exiftool
  radare2 gdb objdump
  wpscan crackmapexec impacket-scripts
  volatility3 autopsy sleuthkit
  maltego recon-ng theharvester
  enum4linux smbclient responder
)

PASS=0; FAIL=0
for tool in "${TOOLS[@]}"; do
  if command -v "$tool" &>/dev/null || dpkg -l "$tool" &>/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $tool"
    ((PASS++))
  else
    echo -e "  ${RED}✗${NC} $tool"
    ((FAIL++))
  fi
done

echo ""
echo -e "${GREEN}  ✓ $PASS tools gevonden${NC}"
[ $FAIL -gt 0 ] && echo -e "${YELLOW}  ! $FAIL tools niet gevonden (zie log hierboven)${NC}"
echo ""
echo "Handige locaties:"
echo "  Wordlists:         /usr/share/wordlists/"
echo "  SecLists:          /usr/share/seclists/"
echo "  Nuclei templates:  ~/.local/nuclei-templates/"
echo "  PEASS scripts:     /opt/PEASS/"
echo "  PayloadsAllThings: /opt/PayloadsAllTheThings/"
echo ""
warn "Herstart je terminal of run: source /etc/profile.d/pentest-tools.sh"
warn "Gebruik tools ALLEEN op systemen waarvoor je toestemming hebt!"
