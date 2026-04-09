# AutoPentest AI Scanner — Ephemeral Container
# Based on Kali Linux with all required pentesting tools
FROM kalilinux/kali-rolling:latest

ENV DEBIAN_FRONTEND=noninteractive

# Core tools + all scan-phase tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Phase 1: Recon
    nmap \
    theharvester \
    amass \
    recon-ng \
    whois \
    dnsenum \
    dnsrecon \
    sublist3r \
    # Phase 2: Vuln Scanning
    nuclei \
    nikto \
    exploitdb \
    # Phase 3: Web App Testing
    zaproxy \
    sqlmap \
    wfuzz \
    gobuster \
    ffuf \
    whatweb \
    wafw00f \
    commix \
    dalfox \
    # Phase 4: Network
    netexec \
    enum4linux \
    smbclient \
    rpcclient \
    ldap-utils \
    impacket-scripts \
    # Phase 5: Auth Testing
    hydra \
    medusa \
    john \
    hashcat \
    patator \
    # Phase 6: SSL/TLS
    testssl.sh \
    sslyze \
    sslscan \
    # Phase 7: Cloud
    trivy \
    # Phase 8: OSINT
    gitleaks \
    # Utilities
    python3 \
    python3-pip \
    curl \
    wget \
    jq \
    iproute2 \
    iptables \
    dnsutils \
    netcat-openbsd \
    seclists \
    && rm -rf /var/lib/apt/lists/*

# Install additional Python tools
RUN pip3 install --no-cache-dir --break-system-packages \
    shodan \
    h8mail \
    scoutsuite \
    cloudsploit \
    prowler

# Copy the scan orchestrator
COPY scripts/ /opt/scanner/
RUN chmod +x /opt/scanner/*.sh /opt/scanner/*.py 2>/dev/null || true

WORKDIR /opt/scanner

# Entrypoint receives scan config as JSON via environment variable
ENTRYPOINT ["python3", "/opt/scanner/entrypoint.py"]
