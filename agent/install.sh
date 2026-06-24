#!/bin/bash
# Scanix Agent installation script
# Usage: curl -sSL https://app.scanix.nl/agent/install.sh | AGENT_TOKEN=xxx bash

set -e
echo "=== Scanix Agent Installatie ==="

if [ -z "${AGENT_TOKEN}" ]; then
  echo "ERROR: AGENT_TOKEN niet ingesteld."
  echo "Gebruik: curl -sSL <url>/agent/install.sh | AGENT_TOKEN=xxx bash"
  exit 1
fi

SCANIX_URL="${SCANIX_URL:-https://app.scanix.nl}"

# Check Python 3
python3 --version || { echo "Python 3 vereist"; exit 1; }

# Ensure requests is available
python3 -c "import requests" 2>/dev/null || pip3 install requests 2>/dev/null || \
  echo "Let op: installeer python3 'requests' handmatig indien nodig."

# Check nmap
which nmap >/dev/null 2>&1 || apt-get install -y nmap 2>/dev/null || \
  echo "Installeer nmap handmatig: apt install nmap"

# Download agent
mkdir -p /opt/scanix-agent
curl -sSL "${SCANIX_URL}/agent/scanix_agent.py" -o /opt/scanix-agent/scanix_agent.py

# Install as systemd service
cat > /etc/systemd/system/scanix-agent.service << EOF
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

systemctl daemon-reload
systemctl enable scanix-agent
systemctl start scanix-agent

echo "=== Agent geïnstalleerd en gestart ==="
echo "Status: systemctl status scanix-agent"
