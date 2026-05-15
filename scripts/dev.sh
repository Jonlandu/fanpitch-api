#!/usr/bin/env bash
# Start the dev backend locally (no Docker).
# Requires: postgres + redis running on default ports, .env populated.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Copied .env.example → .env. Edit it before running again."
  exit 1
fi

python manage.py migrate --noinput
exec daphne -b 0.0.0.0 -p 8000 fanpitch.asgi:application
