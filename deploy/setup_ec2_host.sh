#!/usr/bin/env bash
# FanPitch — bootstrap the EC2 host (runs on the EC2, not on your laptop).
#
# This script installs the runtime + boots the stack. It expects the source
# code AND .env to already be in place on the EC2 — handled by
# `deploy/sync_local.sh` from your laptop, NOT by git clone (the user
# reserves push, so the repo may not yet be on GitHub).
#
# What it does:
#   1. Install Docker + Compose v2 + git + python3
#   2. Build the docker images and start docker-compose.prod.yml
#   3. Run migrations + idempotent demo_setup
#   4. Health-check the API
#
# USAGE (from your laptop, AFTER setup_aws_sandbox.sh + sync_local.sh):
#   ssh -i deploy/artifacts/fanpitch-sandbox-key.pem ec2-user@<EC2_DNS> 'bash -s' < deploy/setup_ec2_host.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/home/ec2-user/fanpitch-api}"

echo "▶ Installing Docker + git + python3 ..."
sudo dnf update -y -q
sudo dnf install -y docker git python3 python3-pip
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# Docker Compose v2 plugin (not bundled with Amazon Linux 2023)
DOCKER_CONFIG=${DOCKER_CONFIG:-/usr/local/lib/docker}
if ! sudo docker compose version >/dev/null 2>&1; then
  echo "▶ Installing Docker Compose v2 plugin ..."
  sudo mkdir -p $DOCKER_CONFIG/cli-plugins
  sudo curl -sSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o $DOCKER_CONFIG/cli-plugins/docker-compose
  sudo chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
fi
echo "✓ Docker $(sudo docker --version) + Compose $(sudo docker compose version --short)"

if [[ ! -d "$APP_DIR" ]]; then
  echo "✗ $APP_DIR missing — did sync_local.sh run?" >&2
  exit 1
fi
if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "✗ $APP_DIR/.env missing — did sync_local.sh push the .env.prod?" >&2
  echo "  From your laptop: bash deploy/sync_local.sh --restart" >&2
  exit 1
fi
cd "$APP_DIR"

echo "▶ Building Docker images (first build ~3 min) ..."
sudo docker compose -f docker-compose.prod.yml build

echo "▶ Starting services (web + worker + beat + redis) ..."
sudo docker compose -f docker-compose.prod.yml up -d

echo "▶ Waiting 15s for services to settle ..."
sleep 15

echo "▶ Running migrations ..."
sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput

echo "▶ Seeding demo data (idempotent — safe to re-run) ..."
sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py demo_setup || true

echo "▶ Health check ..."
sleep 3
EC2_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname || echo "<unknown>")
if curl -sf "http://localhost/api/docs/" >/dev/null; then
  echo "✓ API responding on http://$EC2_DNS/api/docs/"
else
  echo "! API not yet responding — check: sudo docker compose -f docker-compose.prod.yml logs --tail=80 web"
fi

cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ FanPitch backend is live!

  API docs:  http://$EC2_DNS/api/docs/
  Admin:     http://$EC2_DNS/admin/        (admin / admin12345)
  WebSocket: ws://$EC2_DNS/ws/match/1/

  Watch logs:
    sudo docker compose -f docker-compose.prod.yml logs -f web

  Run live demo (separate ssh):
    sudo docker compose -f docker-compose.prod.yml exec web \\
      python manage.py run_demo --speed 10

  Stop the stack to save budget (preserves DB):
    sudo docker compose -f docker-compose.prod.yml stop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
