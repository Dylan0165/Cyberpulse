#!/bin/bash
set -e

echo "=== Scanix Productie Deploy ==="
echo "$(date)"

# Ga naar project directory
cd /opt/scanix

# Pull laatste versie
git pull origin main

# Stop running containers (behalve postgres en redis — data bewaren)
docker compose -f docker-compose.prod.yml stop frontend backend celery_worker celery_beat nginx

# Build nieuwe images
docker compose -f docker-compose.prod.yml build --no-cache frontend backend

# Start alles op
docker compose -f docker-compose.prod.yml up -d

# Wacht op backend
echo "Wachten op backend..."
sleep 15

# Database migraties draaien
docker compose -f docker-compose.prod.yml exec -T backend \
  alembic upgrade head

echo "=== Deploy voltooid! ==="
echo "Frontend: https://app.scanix.nl"
echo "Marketing: https://scanix.nl"
