# Scanix — Productie Deploy Checklist

## Stap 1: Servers aanmaken (OVH)
- [ ] VPS-2 aanmaken: 4 vCores, 8GB RAM — naam: scanix-app
- [ ] VPS-3 aanmaken: 6 vCores, 12GB RAM — naam: scanix-tools
- [ ] Ubuntu 22.04 op beide
- [ ] SSH key toevoegen bij aanmaken

## Stap 2: DNS instellen bij je registrar
- [ ] scanix.nl         → A record → IP van scanix-app
- [ ] www.scanix.nl     → A record → IP van scanix-app
- [ ] app.scanix.nl     → A record → IP van scanix-app
- [ ] Wacht op propagatie (max 24u, vaak <1u)

## Stap 3: App server inrichten (scanix-app)
```
ssh root@[SCANIX-APP-IP]

# Docker installeren
curl -fsSL https://get.docker.com | bash
usermod -aG docker $USER

# SSL certificaten aanvragen
apt install certbot -y
certbot certonly --standalone -d scanix.nl -d www.scanix.nl -d app.scanix.nl
# Vul je email in, accepteer voorwaarden

# Project klonen
git clone https://github.com/Dylan0165/Cyberpulse.git /opt/scanix
cd /opt/scanix

# .env aanmaken
cp .env.production.example .env
nano .env
# Vul ALLE waarden in (wachtwoorden, API keys, etc.)
```

## Stap 4: Tools server inrichten (scanix-tools)
```
ssh root@[SCANIX-TOOLS-IP]

# Kopieer setup script
scp root@[SCANIX-APP-IP]:/opt/scanix/scripts/setup-tools-server.sh /tmp/
scp root@[SCANIX-APP-IP]:/opt/scanix/scanner/tool_api.py /tmp/

# Pas APP_SERVER_IP aan in het script
sed -i 's/APP_SERVER_IP/[SCANIX-APP-IP]/g' /tmp/setup-tools-server.sh

# Draai setup
SCANNER_API_KEY=[JOUW-SCANNER-KEY] bash /tmp/setup-tools-server.sh
```

## Stap 5: GitHub Secrets instellen
Ga naar github.com/Dylan0165/Cyberpulse → Settings → Secrets. Voeg toe:
- [ ] PROD_HOST = IP van scanix-app
- [ ] PROD_USER = root
- [ ] PROD_SSH_KEY = private SSH key inhoud

> De productie-workflow (`.github/workflows/deploy-production.yml`) draait
> **handmatig** (Actions → "Deploy naar productie" → Run workflow). Dit is
> bewust geen automatische trigger op elke push naar `main`.

## Stap 6: Stripe instellen
- [ ] Ga naar dashboard.stripe.com
- [ ] Maak 5 producten aan (1/3/5/10/25 credits)
- [ ] Kopieer de Price IDs naar .env
- [ ] Stel webhook in op: https://app.scanix.nl/api/billing/webhook
- [ ] Events: payment_intent.succeeded, checkout.session.completed,
             customer.subscription.*, invoice.*

## Stap 7: Eerste deploy
```
cd /opt/scanix
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## Stap 8: Admin account aanmaken
```
curl -X POST https://app.scanix.nl/api/admin/init \
  -H "Content-Type: application/json" \
  -d '{"secret": "scanix-admin-init", "email": "jouw@email.nl", "password": "SterkWachtwoord123!"}'
```

## Stap 9: Controleer alles
- [ ] https://scanix.nl laadt correct
- [ ] https://app.scanix.nl laadt correct
- [ ] https://app.scanix.nl/api/health geeft {"status":"healthy"}
- [ ] Registreer een testaccount
- [ ] Start een testscan op scanme.nmap.org
- [ ] Ontvang een email als de scan klaar is
- [ ] Stripe testbetaling werkt

## Auto-renew SSL (crontab)
```
crontab -e
# Voeg toe:
0 3 * * 1 certbot renew --quiet && docker restart scanix-nginx
```

## Docker cleanup (crontab — voorkomt volle disk)
```
0 3 * * * docker system prune -af --volumes >> /tmp/docker-prune.log 2>&1
```
