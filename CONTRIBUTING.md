# Contributing to FanPitch

Thanks for helping build FanPitch — a real-time social match experience for the
AWS World Sports Innovation Cup 2026 (Challenge 3 "Fan Squad").

This document captures **how we ship code** and **how to set yourself up** to
contribute productively. If something here is wrong or out of date, open a PR.

---

## Branch strategy

We use a lightweight **GitFlow** with three protected branches.

```
                       PR + 2 ✓ checks
   feature/* ──────▶ dev ──────▶ staging ──────▶ main (= production)
                                                    │
                                                    └─▶ deploys to AWS EC2
```

| Branch    | Purpose                                                  | Push direct? |
|-----------|----------------------------------------------------------|--------------|
| `main`    | Production. Tagged releases. What runs on AWS EC2.      | ❌ PR only   |
| `staging` | Pre-production. Full CI run. Manual sanity check.       | ❌ PR only   |
| `dev`     | Active integration. Feature merges land here first.     | ❌ PR only   |
| `feature/<short-name>` | One unit of work per branch.                | ✅ Yes       |
| `fix/<short-name>`     | Bug fixes — same lifecycle as feature.       | ✅ Yes       |
| `chore/<short-name>`   | Tooling, deps, infra not user-visible.       | ✅ Yes       |

**Naming**: use kebab-case after the prefix. Examples: `feature/clickable-profile`,
`fix/dio-refresh-401-loop`, `chore/bump-django-5.1.4`.

## Commit messages — Conventional Commits

Every commit must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<body — what changed and why, wrapped at ~72 chars>

<footer — Co-Authored-By, Refs, BREAKING CHANGE: ...>
```

Allowed types (enforced by commitlint in CI):

| Type     | When to use                                                    |
|----------|----------------------------------------------------------------|
| `feat`   | A new user-visible feature                                     |
| `fix`    | A bug fix                                                      |
| `chore`  | Tooling, deps, infra, comments — no behaviour change          |
| `docs`   | Documentation only                                             |
| `refactor` | Internal cleanup, no behaviour change                        |
| `perf`   | Performance improvement                                        |
| `test`   | Adding or fixing tests                                         |
| `build`  | Build system, Docker, CI config                                |
| `style`  | Code style, formatting                                         |
| `revert` | Reverts a previous commit                                      |

Examples:

```
feat(profile): clickable user profile + AppUser is_me/is_following
fix(deploy): escape $30/$40/$45 in log + auto-install buildx
chore(deps): bump Django 5.1.2 → 5.1.4
```

## Pull request workflow

1. **Branch off** the branch you target (typically `dev`).
2. **Commit early, commit small**. Each commit should be reviewable on its own.
3. **Open the PR** as soon as you have something to discuss — draft is fine.
4. **Fill the PR template** (`.github/PULL_REQUEST_TEMPLATE.md`): summary, test
   plan, breaking-change flag.
5. **Pass all required checks**:
   - `lint-python` (ruff + bandit security)
   - `test-python` (pytest)
   - `lint-flutter` (flutter analyze) — only when `fanpitch-app/**` changes
   - `trivy-image` (Docker image vulnerability scan)
   - `codeql-python` (SAST)
   - `commitlint` (Conventional Commits)
6. **Request review**. Branch protection requires at least one approval.
7. **Squash-merge** unless the PR is a series of meaningful commits (release PRs).

## Local dev setup

```bash
git clone https://github.com/Jonlandu/fanpitch-api.git
cd fanpitch-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # then edit
bash scripts/setup_db.sh         # one-time Postgres bootstrap
python manage.py migrate
python manage.py demo_setup      # idempotent seed
daphne -b 0.0.0.0 -p 8000 fanpitch.asgi:application
```

See [`../RUN.md`](../RUN.md) for the 5-minute end-to-end flow with the mobile app.

## Code style

- **Python**: ruff (line length 100, Django conventions). Run `ruff check apps/`.
- **Security linter**: `bandit -r apps/` (catches obvious XSS/SQL-injection/etc).
- **No `# noqa`** without a comment explaining why.
- **No `# type: ignore`** without a comment explaining why.
- **Type hints** on every public function signature, including `-> None`.

## Tests

- **Unit tests** under `apps/<app>/tests/test_<thing>.py`.
- **Integration tests** under `tests/` at the repo root.
- **Don't mock the database** for tests that exercise migrations or signals —
  use the real Postgres in CI (services: postgres in the workflow).

Run locally:
```bash
pytest -x
```

## Releasing

`main` is always deployable. To cut a release:

1. PR `staging` → `main` once staging is verified.
2. Tag the merge commit: `git tag v0.X.0 && git push --tags`.
3. The deploy workflow (`.github/workflows/deploy.yml`, manual `workflow_dispatch`)
   syncs the code to the AWS EC2 and restarts the docker-compose stack.

## Reporting bugs / security issues

- **Bug**: open an issue with the **Bug report** template.
- **Feature idea**: open an issue with the **Feature request** template.
- **Security vulnerability**: do NOT open a public issue. Email the maintainer
  (`Development@bmprimecapital.com`) or file a private security advisory on
  GitHub. See [`SECURITY.md`](SECURITY.md) for our disclosure policy.

## Code of conduct

Be kind, be specific, be honest. We're building this together for a competition
that we want to win — assume good intent, push back on ideas not people.
