# FanPitch Backend

[![CI](https://github.com/Jonlandu/fanpitch-api/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Jonlandu/fanpitch-api/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Jonlandu/fanpitch-api/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/Jonlandu/fanpitch-api/actions/workflows/codeql.yml)
[![Security](https://github.com/Jonlandu/fanpitch-api/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/Jonlandu/fanpitch-api/actions/workflows/security.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 5.1](https://img.shields.io/badge/django-5.1-092E20.svg?logo=django&logoColor=white)](https://djangoproject.com)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196.svg)](https://www.conventionalcommits.org)

> **Real-time social match experience** for the AWS World Sports Innovation Cup 2026 — Challenge 3 "Fan Squad".

Django 5 + DRF + Channels (WebSocket) + Celery, deployed on AWS EC2 + RDS + S3 + Bedrock (Innovation Sandbox, `eu-central-1`).

**Live demo URLs**
- API docs (Swagger): http://ec2-63-184-221-33.eu-central-1.compute.amazonaws.com/api/docs/
- Admin: http://ec2-63-184-221-33.eu-central-1.compute.amazonaws.com/admin/ (`admin / admin12345`)
- Mobile companion: [`fanpitch-app`](https://github.com/Jonlandu/fanpitch-app)

**Demo fan accounts** (20 seeded, all share password `fanpitch2026`):
`congo_general`, `lisbon_lion`, `paris_fan`, `messi_devoto`, `samba_king`, `atlas_lion`, `teranga_fan`, `indomitable_fan`, `la_furia`, `naija_naija` … (full list: `python manage.py seed_world_cup`)

- 🏗️ **Architecture overview** → [`ARCHITECTURE.md`](ARCHITECTURE.md)
- 🛠️ **5-minute local quick-start** → [`../RUN.md`](../RUN.md)
- ☁️ **AWS deployment guide** → [`deploy/README.md`](deploy/README.md)
- 🎯 **Hackathon submission package** → [`fanpitch-app/deliverables/`](https://github.com/Jonlandu/fanpitch-app/tree/main/deliverables)
- 🤝 **How to contribute** → [`CONTRIBUTING.md`](CONTRIBUTING.md)
- 🔒 **Security policy** → [`SECURITY.md`](SECURITY.md)

## App layout

```
fanpitch-api/
├── fanpitch/                Django project (settings, asgi, celery_app, urls)
└── apps/
    ├── accounts/            User, Profile, Follow, JWT auth
    ├── matches/             Team, Match, MatchEvent, simulator, Football-Data
    ├── feed/                Status (7-day TTL), MediaPost, S3 presigned uploads
    ├── interactions/        Reaction, Prediction, Poll, PollVote, Comment
    ├── gamification/        Badge, UserBadge, PointsEvent, leaderboard
    ├── ai/                  Bedrock client (captions, memes) + flag
    └── realtime/            Channels consumers + JWT WS middleware
```

## Key commands

```bash
# Migrations
python manage.py migrate

# Seed the 10-team World Cup-style demo (20 fan accounts + 8 matches)
python manage.py seed_world_cup
# Optional alternate seed: text-only fan posts
python manage.py seed_demo_posts

# Or the lighter "Portugal vs DR Congo" seed:
python manage.py demo_setup

# Run the live simulator (in another terminal, after the server is up)
python manage.py run_simulator --match-id 1 --speed 10

# Django admin
python manage.py createsuperuser   # or use the one demo_setup creates
# admin / admin12345

# Run the ASGI server (HTTP + WebSocket)
daphne -b 0.0.0.0 -p 8000 fanpitch.asgi:application

# Celery worker (prediction scoring, badges)
celery -A fanpitch worker -l info
```

## API quick reference

| Endpoint | Method | What |
|---|---|---|
| `/api/v1/auth/register/` | POST | Create user → JWT |
| `/api/v1/auth/login/` | POST | Username/password → JWT |
| `/api/v1/auth/refresh/` | POST | Refresh access token |
| `/api/v1/auth/me/` | GET/PATCH | Current user + profile |
| `/api/v1/matches/` | GET | List matches (filter `?status=LIVE`) |
| `/api/v1/matches/<id>/` | GET | Match detail + recent events |
| `/api/v1/matches/<id>/events/` | GET | All events (or `?since=<minute>`) |
| `/api/v1/statuses/` | GET/POST | 1-week feed |
| `/api/v1/media/upload-url/` | POST | S3 presigned PUT |
| `/api/v1/predictions/` | POST | Submit prediction |
| `/api/v1/polls/` | GET/POST | List/create polls |
| `/api/v1/polls/<id>/vote/` | POST | Vote on a poll |
| `/api/v1/reactions/` | POST | React to a target |
| `/api/v1/leaderboard/` | GET | `?scope=global|week|match` |
| `/api/v1/ai/caption/` | POST | Bedrock caption (or fallback) |
| `/api/v1/ai/meme/` | POST | Bedrock meme (or fallback) |
| `ws://.../ws/match/<id>/?token=<JWT>` | WS | Live match room |

Auto OpenAPI docs at http://localhost:8000/api/docs/.

## Env vars (`.env`)

See `.env.example`. The important toggles:

- `BEDROCK_ENABLED=false` (default) → free fallback jokes; flip to `true` after configuring AWS creds.
- `FOOTBALL_DATA_API_KEY=` → optional; if blank we always use the simulator.
- `S3_BUCKET=` + AWS creds → optional; if blank, uploads fall back to local media path.

## Tests

```bash
python manage.py test
```

Add tests under `tests/` or per app. We ship the structure; concrete tests are a hackathon Day-4 polish item.
