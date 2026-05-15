# FanPitch Backend

Django 5 + DRF + Channels (WebSocket) + Celery, deployed locally on PostgreSQL + Redis.

See [`../RUN.md`](../RUN.md) for the 5-minute quick start and [`../docs/AWS_DEPLOY.md`](../docs/AWS_DEPLOY.md) for the AWS path.

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

# Seed teams + demo fans + Portugal vs DR Congo match
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
