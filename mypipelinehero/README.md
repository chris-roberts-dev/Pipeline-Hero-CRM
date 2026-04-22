# MyPipelineHero CRM

Multi-tenant CRM and operations platform built on Django 5.2 LTS, Python 3.13, and PostgreSQL 17.

See [`requirements.md`](./requirements.md) for the full product and architecture specification.

---

## Status

**Phase 1, Milestone 1 — Platform Foundation** (in progress).

This repo currently contains the Docker-first scaffolding: project layout, compose stack, settings module split, and placeholder apps. No models or migrations yet — the custom user model and tenancy base arrive next.

---

## Prerequisites

- **Docker Desktop** 4.30+ (or Docker Engine 24+ with Compose v2 on Linux)
- **Make** (optional — every `make` target has a plain `docker compose` equivalent)
- ~4 GB of free RAM for the full stack

You do **not** need a local Python install. Everything runs inside containers.

---

## First-Time Setup

### 1. Clone and configure

```bash
git clone <repo-url> mypipelinehero
cd mypipelinehero
cp .env.example .env
```

Open `.env` and **generate a real `DJANGO_SECRET_KEY`**:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Paste the output into the `DJANGO_SECRET_KEY=` line.

Every other default in `.env.example` is fine for local dev.

### 2. Build and start the stack

```bash
make up        # or: docker compose up -d
```

First build takes a few minutes (Python base image + dependency install). Subsequent starts are seconds.

### 3. Verify the stack is healthy

```bash
docker compose ps
```

Every service should show `Up` and, where applicable, `(healthy)`. Then:

```bash
# Any OS — plain localhost resolves everywhere
curl http://localhost/healthz
# -> {"status": "ok"}
```

If that returns JSON, the nginx → django → postgres → redis path is working. To test tenant subdomain routing, see the next section — it varies by OS.

---

## Local Subdomain Routing

The platform uses the pattern `{slug}.mypipelinehero.localhost` for tenant portals. Resolution support is not uniform across operating systems and tools — read the section for your OS.

### Key distinction: browsers vs. shell tools

Some browsers resolve `*.localhost` automatically per RFC 6761. **Shell tools like `curl`, PowerShell's `Invoke-WebRequest`, Python, and httpie generally do NOT** — they go through the OS resolver, which varies. Adding hosts-file entries is the universally reliable option.

### Windows (PowerShell / cmd)

Windows does not auto-resolve `*.localhost` at the OS level. Edit the hosts file:

1. Open Notepad **as Administrator** (right-click → Run as administrator).
2. File → Open → `C:\Windows\System32\drivers\etc\hosts` (switch the file picker filter to "All Files").
3. Add:

   ```
   127.0.0.1  mypipelinehero.localhost
   127.0.0.1  acme.mypipelinehero.localhost
   127.0.0.1  beta.mypipelinehero.localhost
   ```

4. Save. Takes effect immediately, no reboot.

Then test — note that PowerShell's `curl` is aliased to `Invoke-WebRequest` and behaves differently from real curl. Use `curl.exe` for the Unix-compatible tool (ships with Windows 10+):

```powershell
curl.exe http://mypipelinehero.localhost/healthz
```

Chrome, Firefox, and Edge on Windows will also honor the hosts file, and most recent versions additionally auto-resolve `*.localhost` at the browser level — so browser access works with or without hosts entries.

### macOS / Linux — Chrome, Firefox, Edge

Browsers resolve any `*.localhost` hostname to `127.0.0.1` automatically (per RFC 6761). Open:

- `http://mypipelinehero.localhost` — root domain / login landing page
- `http://acme.mypipelinehero.localhost` — hypothetical tenant portal for "acme"

### macOS — Safari and shell tools (curl, httpie, Python)

Safari does **not** auto-resolve `*.localhost`, and neither do command-line tools on macOS by default. Add entries to `/etc/hosts`:

```bash
sudo sh -c 'cat >> /etc/hosts <<EOF
127.0.0.1  mypipelinehero.localhost
127.0.0.1  acme.mypipelinehero.localhost
127.0.0.1  beta.mypipelinehero.localhost
EOF'
```

Or install `dnsmasq` to resolve the entire `.localhost` TLD automatically:

```bash
# macOS with Homebrew
brew install dnsmasq
echo 'address=/localhost/127.0.0.1' >> $(brew --prefix)/etc/dnsmasq.conf
sudo brew services start dnsmasq
sudo mkdir -p /etc/resolver
echo 'nameserver 127.0.0.1' | sudo tee /etc/resolver/localhost
```

### Linux — shell tools (curl, httpie, Python)

Most distros resolve `localhost` (but not `*.localhost`) via `/etc/hosts` by default. Add the entries shown in the macOS section above to the same file (`/etc/hosts`) with `sudo`, and every tool that uses the system resolver will pick them up.

---

## Daily Workflow

```bash
make up          # start everything
make logs        # tail logs (Ctrl-C detaches; stack keeps running)
make shell       # Django shell inside the django container
make dbshell     # psql into postgres
make test        # run pytest
make lint        # ruff check
make format      # ruff format
make down        # stop the stack (volumes persist)
```

Source code is bind-mounted into the `django`, `celery_worker`, and `celery_beat` containers. Python file changes hot-reload for `django` via `runserver`. **Celery workers do not auto-reload** — restart them with `docker compose restart celery_worker celery_beat` after editing task code.

---

## Project Layout

```
mypipelinehero/
├── config/             Django project package (settings, urls, wsgi, celery)
│   └── settings/       Per-environment settings modules (base, dev, test, prod)
├── apps/               All application code, grouped by domain
│   ├── platform/       accounts, organizations, rbac, audit, support
│   ├── web/            landing (login), auth_portal (handoff), tenant_portal
│   ├── crm/            leads, quotes, clients, tasks, communications, orders, billing
│   ├── catalog/        services, products, materials, suppliers, pricing, manufacturing
│   ├── operations/     locations, purchasing, build, workorders
│   ├── files/          attachments (document storage abstraction)
│   ├── reporting/      exports (fixed reports + CSV)
│   ├── api/            Phase 2 — internal JSON API (not populated in Phase 1)
│   └── common/         tenancy, services, outbox, utils, admin, tests
├── docker/             Dockerfiles and nginx config
├── requirements/       Pinned pip requirements split by environment
├── templates/          Django templates (shared base; per-app templates live in apps/)
├── static/ media/      Static files and uploaded media (dev only for media)
├── frontend/           Phase 2 — React SPA source (not populated in Phase 1)
├── compose.yaml        Full local dev stack
├── Makefile            Convenience commands
└── .env.example        Documented environment variables
```

Every app listed above currently ships as an empty `INSTALLED_APPS` placeholder. Models, admin, views, and services are added milestone by milestone.

---

## Environments

Three settings modules live under `config/settings/`:

| Module | Loaded via | Purpose |
|---|---|---|
| `config.settings.dev`  | compose default | Local development: DEBUG on, console email, plain-text logs |
| `config.settings.test` | `pytest` auto   | Test suite: eager Celery, locmem cache, MD5 hashing |
| `config.settings.prod` | deployment env  | Production: Sentry, S3 storage, HSTS, secure cookies |

Override via `DJANGO_SETTINGS_MODULE` in the environment or `.env`.

---

## Services in the Stack

| Service | Image | Purpose |
|---|---|---|
| `postgres`      | `postgres:17-alpine`    | Primary database |
| `redis`         | `redis:7-alpine`        | Cache, Celery broker/results, handoff tokens |
| `django`        | `mph-django:dev`        | Web application (`runserver` in dev) |
| `celery_worker` | `mph-django:dev`        | Async task execution |
| `celery_beat`   | `mph-django:dev`        | Scheduled task dispatch (DB-backed scheduler) |
| `nginx`         | built from `docker/nginx/` | Reverse proxy on `:80` with wildcard `*.localhost` routing |

**pgBouncer** is **required in production** (spec §24.3A) and intentionally **omitted in local dev** to keep the debugging surface small.

---

## Troubleshooting

**PowerShell `curl` returns `The remote name could not be resolved`**
Two things. (1) Windows doesn't auto-resolve `*.localhost` — you need hosts-file entries; see "Local Subdomain Routing → Windows" above. (2) PowerShell's `curl` is an alias for `Invoke-WebRequest`, not the real curl. Use `curl.exe` for Unix-compatible behavior, or `Invoke-WebRequest -Uri http://...`.

**`ALLOWED_HOSTS` errors on `{slug}.mypipelinehero.localhost`**
Make sure `.env` contains `DJANGO_ALLOWED_HOSTS=.localhost,127.0.0.1,0.0.0.0`. The leading dot enables wildcard matching.

**`django` container exits immediately on first start**
Usually a missing or empty `DJANGO_SECRET_KEY`. Check `.env`, then `docker compose logs django`.

**Safari can't reach `http://acme.mypipelinehero.localhost`**
Safari doesn't support the `*.localhost` auto-resolve. Add entries to `/etc/hosts` or install `dnsmasq` — see "Local Subdomain Routing → macOS" above.

**`pytest` can't connect to Postgres**
Tests use the same `postgres` container as dev. Make sure it's up: `docker compose ps postgres`. If running tests from the host instead of the container, remember that `postgres` as a hostname only resolves inside the compose network — use `localhost:5432` from the host.

**Celery tasks don't pick up code changes**
Celery workers don't auto-reload. Restart them: `docker compose restart celery_worker celery_beat`.

---

## What's Next

Milestone 1 continues with:
- Custom user model (`apps.platform.accounts.User`) — email as primary identifier
- `Organization` + `Membership` models + tenancy base (`TenantQuerySet`, `TenantManager`)
- `TenancyMiddleware` to resolve `{slug}.mypipelinehero.localhost` to an active organization
- Central login landing page, org picker, and cross-subdomain handoff token flow
- `AuditEvent` model skeleton

See `requirements.md` §6–10 for the authoritative definitions.
