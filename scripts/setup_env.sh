#!/usr/bin/env bash
# Run once on the server to prepare the deployment environment.
# Does NOT contain secrets — fill in .env manually after this script completes.
set -euo pipefail

REPO_URL="https://github.com/$(git config --get remote.origin.url | sed 's|.*github.com[:/]\(.*\)\.git|\1|')"
DEPLOY_DIR="/home/student/cyberpulse"
DEPLOY_USER="student"

echo "[1/3] Cloning repository to ${DEPLOY_DIR}..."
if [ -d "${DEPLOY_DIR}/.git" ]; then
  echo "  Repo already exists at ${DEPLOY_DIR}, skipping clone."
else
  sudo -u "${DEPLOY_USER}" git clone "${REPO_URL}" "${DEPLOY_DIR}"
fi

echo "[2/3] Creating .env from .env.example..."
if [ -f "${DEPLOY_DIR}/.env" ]; then
  echo "  .env already exists, skipping. Edit it manually if needed."
else
  cp "${DEPLOY_DIR}/.env.example" "${DEPLOY_DIR}/.env"
  chown "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_DIR}/.env"
  chmod 600 "${DEPLOY_DIR}/.env"
  echo "  Created ${DEPLOY_DIR}/.env — fill in all secret values before deploying."
fi

echo "[3/3] Adding ${DEPLOY_USER} to the docker group..."
if id -nG "${DEPLOY_USER}" | grep -qw docker; then
  echo "  ${DEPLOY_USER} is already in the docker group."
else
  usermod -aG docker "${DEPLOY_USER}"
  echo "  Done. The user must log out and back in (or run 'newgrp docker') for this to take effect."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit ${DEPLOY_DIR}/.env and fill in all required secrets."
echo "  2. Register the GitHub Actions self-hosted runner on this machine."
echo "  3. Push to main to trigger the first deployment."
