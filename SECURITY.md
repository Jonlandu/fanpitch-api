# Security policy

## Supported versions

Until v1.0.0, only the `main` branch is supported. Older tags receive no
security backports.

| Version | Supported          |
|---------|--------------------|
| 0.x     | :white_check_mark: |

## Reporting a vulnerability

We take security seriously. If you discover a vulnerability in FanPitch:

1. **Do NOT open a public issue** — that would tip off attackers before we
   can patch.
2. Use one of the private channels:
   - **GitHub Security Advisory** (preferred):
     https://github.com/Jonlandu/fanpitch-api/security/advisories/new
   - **Email**: `Development@bmprimecapital.com` (subject: `[SECURITY] FanPitch`)

Please include:
- A clear description of the vulnerability.
- Steps to reproduce (proof-of-concept).
- The impact you anticipate (data leak, privilege escalation, denial of service…).
- Your name and how you'd like to be credited (or "anonymous" — we respect both).

**We commit to**:
- Acknowledging your report within **72 hours**.
- Publishing a fix within **14 days** for high/critical severity.
- Crediting you in the release notes (unless you prefer anonymity).

## What's in scope

- The FanPitch backend (`fanpitch-api`) and mobile app (`fanpitch-app`).
- The deployment scripts under `deploy/`.
- The Docker image and runtime configuration.
- Default seeded credentials and demo data (note: they are **demo only** and
  must NOT be reused in production; this is documented in `RUN.md`).

## What's out of scope

- Vulnerabilities in third-party dependencies — please report those upstream.
  We use Dependabot to track and patch them.
- Issues that require physical access to a device.
- Issues that require an attacker to already have root on the EC2.
- The AWS sandbox itself — that's owned by AWS / Slalom.

## Security controls in place

The repo runs the following automated checks on every PR and weekly:

| Tool          | What it does                                            |
|---------------|---------------------------------------------------------|
| **CodeQL**    | Static analysis on Python for OWASP top-10 patterns.    |
| **Bandit**    | Python-specific security linter (eval, hardcoded secrets, weak crypto). |
| **Trivy**     | Vulnerability scan of the built Docker image.           |
| **Dependabot**| Weekly PRs for vulnerable Python deps.                  |
| **Secret scanning** | GitHub-native; refuses any push containing a known credential pattern. |
| **Branch protection** | `main` requires PR + passing checks + approval.   |

## Known limitations

- Demo credentials are seeded by `python manage.py demo_setup` for the
  hackathon demo. They are printed to stdout and never committed to the repo.
  When you adapt the project to production, replace the seeded users.
- `DJANGO_DEBUG` must be `False` in production — checked at deploy time in
  `setup_ec2_host.sh`.
- The AWS Innovation Sandbox lease has a 4-hour credential TTL. Don't bake
  credentials into the Docker image; use the IAM instance profile attached
  to the EC2 (`FanPitchAppRole`).
