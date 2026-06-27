#!/bin/bash
# Scanix Agent installation script
# Usage: curl -sSL <SCANIX_URL>/agent/install.sh | SCANIX_URL=<SCANIX_URL> AGENT_TOKEN=xxx bash
# SCANIX_URL defaults to the test/netlab IP; set it to your app URL in production.
# Needs root for apt / /opt / systemd — auto-uses sudo when not run as root.

set -e
echo "=== Scanix Agent Installatie ==="

if [ -z "${AGENT_TOKEN}" ]; then
  echo "ERROR: AGENT_TOKEN niet ingesteld."
  echo "Gebruik: curl -sSL <url>/agent/install.sh | AGENT_TOKEN=xxx bash"
  exit 1
fi

SCANIX_URL="${SCANIX_URL:-http://192.168.121.40}"

# Privilege escalation: prefix privileged commands with sudo when not root.
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
    echo "Niet als root — sudo wordt gebruikt (mogelijk wordt om een wachtwoord gevraagd)."
  else
    echo "ERROR: draai dit als root of installeer sudo."
    exit 1
  fi
fi

# Check Python 3
python3 --version || { echo "Python 3 vereist"; exit 1; }

# Ensure requests is available
python3 -c "import requests" 2>/dev/null || \
  $SUDO pip3 install requests --break-system-packages 2>/dev/null || \
  echo "Let op: installeer python3 'requests' handmatig indien nodig."

# Check nmap
which nmap >/dev/null 2>&1 || $SUDO apt-get install -y nmap 2>/dev/null || \
  echo "Installeer nmap handmatig: sudo apt install nmap"

# Download agent
$SUDO mkdir -p /opt/scanix-agent
$SUDO curl -sSL "${SCANIX_URL}/agent/scanix_agent.py" -o /opt/scanix-agent/scanix_agent.py

# Install as systemd service (write via sudo tee so the redirect runs as root)
$SUDO tee /etc/systemd/system/scanix-agent.service > /dev/null << EOF
[Unit]
Description=Scanix Security Agent
After=network.target

[Service]
Type=simple
Environment=AGENT_TOKEN=${AGENT_TOKEN}
Environment=SCANIX_URL=${SCANIX_URL}
ExecStart=/usr/bin/python3 /opt/scanix-agent/scanix_agent.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

$SUDO systemctl daemon-reload
$SUDO systemctl enable scanix-agent
$SUDO systemctl start scanix-agent

echo "=== Agent geïnstalleerd en gestart ==="
echo "Status: sudo systemctl status scanix-agent"
