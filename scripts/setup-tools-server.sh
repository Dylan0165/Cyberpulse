#!/bin/bash
# Draai dit 1x op de OVH tools server (VPS-3)
set -e

echo "=== Scanix Tools Server Setup ==="

# Update
apt-get update && apt-get upgrade -y

# Installeer Kali tools
apt-get install -y \
  nmap nikto sqlmap hydra testssl.sh \
  python3 python3-pip python3-venv \
  curl wget git unzip

# Installeer nuclei
wget https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_linux_amd64.zip
unzip -o nuclei_linux_amd64.zip -d /usr/local/bin/
chmod +x /usr/local/bin/nuclei
nuclei -update-templates

# Installeer ffuf
wget https://github.com/ffuf/ffuf/releases/latest/download/ffuf_linux_amd64.tar.gz
tar -xzf ffuf_linux_amd64.tar.gz -C /usr/local/bin/
chmod +x /usr/local/bin/ffuf

# Installeer theHarvester
pip3 install theHarvester --break-system-packages

# Installeer gitleaks
wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_linux_x64.tar.gz
tar -xzf gitleaks_linux_x64.tar.gz -C /usr/local/bin/
chmod +x /usr/local/bin/gitleaks

# Setup tool_api.py
mkdir -p /opt/scanix-tools
cp /tmp/tool_api.py /opt/scanix-tools/
cd /opt/scanix-tools
pip3 install fastapi uvicorn python-multipart requests --break-system-packages

# Systemd service voor tool_api.py
cat > /etc/systemd/system/scanix-tools.service << EOF
[Unit]
Description=Scanix Tools API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/scanix-tools
Environment=SCANNER_API_KEY=${SCANNER_API_KEY}
ExecStart=/usr/bin/python3 -m uvicorn tool_api:app --host 0.0.0.0 --port 5001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scanix-tools
systemctl start scanix-tools

# Firewall: alleen poort 5001 open voor app server
ufw allow ssh
ufw allow from APP_SERVER_IP to any port 5001
ufw --force enable

echo "=== Tools server setup klaar ==="
echo "tool_api.py draait op :5001"
