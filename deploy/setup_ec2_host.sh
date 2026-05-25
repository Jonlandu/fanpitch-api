#!/usr/bin/env bash
# FanPitch — bootstrap the EC2 host (runs on the EC2, not on your laptop).
#
# This script:
#   1. Installs Docker + git
#   2. Clones the FanPitch repo (or pulls latest)
#   3. Copies /tmp/.env -> fanpitch-api/.env  (uploaded via scp before this runs)
#   4. Builds and starts docker-compose.prod.yml
#   5. Runs migrations + demo_setup (idempotent)
#   6. Prints API health check URL
#
# USAGE (from your laptop, after setup_aws_sandbox.sh):
#   scp -i deploy/artifacts/fanpitch-sandbox-key.pem deploy/artifacts/.env.prod \
#       ec2-user@<EC2_DNS>:/tmp/.env
#   ssh -i deploy/artifacts/fanpitch-sandbox-key.pem ec2-user@<EC2_DNS> 'bash -s' < deploy/setup_ec2_host.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/YOUR-GITHUB/fanpitch-api.git}"
APP_DIR="${APP_DIR:-/home/ec2-user/fanpitch-api}"

echo "▶ Installing Docker + git + python3 ..."
sudo dnf update -y
sudo dnf install -y docker git python3 python3-pip
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# Install docker compose v2 plugin (Amazon Linux 2023 doesn't include it by default)
DOCKER_CONFIG=${DOCKER_CONFIG:-/usr/local/lib/docker}
sudo mkdir -p $DOCKER_CONFIG/cli-plugins
sudo curl -sSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o $DOCKER_CONFIG/cli-plugins/docker-compose
sudo chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
echo "✓ Docker + Compose v2 ready ($(docker compose version 2>/dev/null || echo 'reboot may be needed for ec2-user group'))"

echo "▶ Cloning / pulling FanPitch backend repo ..."
if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR" && git pull --rebase
else
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

if [[ ! -f /tmp/.env ]]; then
  echo "✗ /tmp/.env missing — did you scp it up? Aborting." >&2
  exit 1
fi
cp /tmp/.env "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
echo "✓ .env in place."

echo "▶ Building Docker images (this takes ~3 min on first run) ..."
sudo docker compose -f docker-compose.prod.yml build

echo "▶ Starting services ..."
sudo docker compose -f docker-compose.prod.yml up -d

echo "▶ Waiting 15s for services to settle ..."
sleep 15

echo "▶ Running migrations ..."
sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput

echo "▶ Seeding demo data (idempotent) ..."
sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py demo_setup || true

echo "▶ Health check ..."
sleep 3
EC2_DNS=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)
if curl -sf "http://localhost/api/docs/" >/dev/null; then
  echo "✓ API responding."
else
  echo "! API not yet responding — check logs with: sudo docker compose -f docker-compose.prod.yml logs -f web"
fi

cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ FanPitch backend is live!

  API docs:  http://$EC2_DNS/api/docs/
  Admin:     http://$EC2_DNS/admin/        (admin / admin12345)
  WebSocket: ws://$EC2_DNS/ws/match/1/

  To watch logs:
    sudo docker compose -f docker-compose.prod.yml logs -f web

  To run the live match simulator (in a separate ssh session):
    sudo docker compose -f docker-compose.prod.yml exec web \\
      python manage.py run_simulator --match-id 1 --speed 10

  Cost-saving: stop the stack when not demoing:
    sudo docker compose -f docker-compose.prod.yml stop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
