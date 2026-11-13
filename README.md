# FastAPI Auth Starter

A small synchronous SQLAlchemy + FastAPI starter with JWT bearer authentication,
validated registration, database migrations, safe response schemas, health checks,
configurable CORS, request logging, tests, and GitHub Actions CI.

## Run locally

Requires Python 3.12 or later. From the repository directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Put the generated value in `SECRET_KEY` in `.env`. Do not overwrite an existing
`.env` when setting up a checkout that already has local configuration.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload --no-access-log --no-proxy-headers
```

On Linux/macOS, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`,
and `cp .env.example .env` to create the configuration file.

- Swagger: <http://127.0.0.1:8002/docs>
- Liveness: `GET /health`
- Readiness: `GET /health/ready` (503 if the database/users table is unavailable)

Migrations are an explicit deployment step; starting the server does not create
or change tables. SQLite is the default. Existing databases with a different
schema require a separate data migration; the initial migration expects an empty
database. Back up existing data before changing its schema.

## Authentication

1. `POST /register` with JSON:

   ```json
   {"username": "demo_user", "email": "demo@example.com", "password": "a-long-password"}
   ```

   Returns 201 with `id`, `username`, `email`, `admin`, and `disabled`.
   Duplicate identities return 409; invalid data returns 422. Passwords and hashes
   are excluded from responses, including validation errors. Registration rejects
   `admin`, `disabled`, and other unknown fields.

2. `POST /token` with form-encoded `username` and `password`. The `username` field
   accepts either username or email. The response contains `access_token` and
   `token_type: bearer`.
3. Send `Authorization: Bearer <access_token>` to `GET /users/me/`.

Usernames contain 3–50 ASCII letters, numbers, or underscores. Usernames and emails
are normalized to lowercase, including during login. Passwords must contain at
least 8 characters and at most 72 UTF-8 bytes (bcrypt's limit). Passwords are never
trimmed or silently truncated. `admin` and `disabled` are stored in the database;
changing them is an internal administrative operation, with no public endpoint.
Disabled accounts cannot log in, and existing tokens cannot access protected routes.

JWT subjects contain stable user IDs. Tokens require `sub` and `exp`. Old tokens
from the earlier username-based implementation must be replaced by signing in again.
There is no logout/revocation or refresh-token mechanism; tokens expire after the
configured lifetime, and disabling an account blocks further authenticated requests.
The `admin` flag is available for future policies; this starter has no admin routes.

## Configuration

Settings are read from environment variables and the repository's `.env` file.
Environment variables take precedence. See [.env.example](.env.example).

| Variable | Default / requirement |
| --- | --- |
| `SECRET_KEY` | Required; at least 32 characters. Generate a random secret per project/environment. |
| `DATABASE_URL` | SQLite `dev.db`, anchored to the project directory |
| `APP_NAME` | `FastAPI Auth Starter` |
| `ALGORITHM` | `HS256`; also supports `HS384` and `HS512` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30; allowed range 1–1440 |
| `CORS_ORIGINS` | `[]`; JSON array, e.g. `["http://localhost:3000"]` |
| `LOG_LEVEL` | `INFO` |
| `LOGIN_RATE_LIMIT` | 10 requests per client IP per window |
| `REGISTER_RATE_LIMIT` | 5 requests per client IP per window |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 |
| `RATE_LIMIT_STORAGE_URI` | `memory://` locally; use `redis://...` or `rediss://...` for shared counters |
| `RATE_LIMIT_PREFIX` | `fastapi-auth`; use a distinct prefix for each project/environment |

For another SQLAlchemy database, install its driver and change `DATABASE_URL`
(for example `postgresql+psycopg://...` with `psycopg`). The included CI exercises
SQLite; test migrations and constraints against your deployment database too.
Legacy `DB_HOST`, `DB_USER`, etc. are not used; configure a single `DATABASE_URL`.

CORS allows configured origins, GET/POST/OPTIONS, and Authorization/Content-Type
headers. Cookie credentials are disabled. Extend methods when adding other routes.
Logs contain the method, route template, status and duration, without request
bodies, query strings, authorization headers, or SQL parameters. Unexpected errors
return a generic 500 and log the exception class. Keep proxy/access logs equally
careful about credentials and personal data.

## Develop and test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m alembic check
```

Tests migrate isolated temporary databases and use a test signing key. They never
use the local `dev.db`. CI runs checks on Python 3.12 and 3.14.

Redis integration tests are skipped locally unless `TEST_REDIS_URL` points to a
test Redis service. They use unique prefixes and short-lived counters without
flushing the Redis database. CI always runs them against a disposable Redis service:

```powershell
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
.\.venv\Scripts\python.exe -m pytest -q -m redis
```

Run the dependency vulnerability scan with:

```powershell
.\.venv\Scripts\python.exe -m pip_audit -r requirements-dev.txt --progress-spinner off
```

## CI and automatic deployment

The single workflow in `.github/workflows/ci.yml` runs for pushes and pull requests:

1. Python 3.12/3.14: lint, formatting, dependency compatibility, migrations and tests.
2. Dependency security: audit runtime and development dependencies; findings or
   audit errors fail the job, with no vulnerability exceptions.
3. Redis integration: check shared budgets across workers, atomic increments,
   window expiry and HTTP rate limiting against a real Redis service.
4. Deployment: runs only for a push to `main`, after all three jobs pass. Pull
   requests and pushes to other branches never deploy. Deployments are serialized.
5. Readiness: `/health/ready` must return success after the service starts.

Checks use GitHub-hosted runners. Deployment retains the existing self-hosted runner
labels (`self-hosted`, `Linux`, `X64`, `fastapi-auth`), systemd unit (`fastapi-auth`),
and server deployment script (`/usr/local/bin/deploy-fastapi-auth`, run as `fastapiapp`).
The checkout is pinned to the checked commit. The external server script is not
in this repository: verify that it deploys that checkout/commit, installs the updated
requirements and runs `alembic upgrade head` before starting the service. A script
that independently pulls a newer `main` commit could deploy code that has not passed
this workflow. A failed readiness check marks deployment failed; automated rollback
and database backup must be provided by your server deployment tooling.

GitHub repository rules should also require the checks before merging into `main`.
These rules are configured separately in GitHub; changing workflow YAML does not
enable branch protection. Production secrets remain on the server, outside CI test
settings. No manual approval is configured: successful checks on `main` deploy
automatically. The former duplicate deployment workflows were removed.

After changing a SQLAlchemy model:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe the change"
# Review the generated migration before applying it.
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Layout

```text
app/core/          Environment settings
app/models/        SQLAlchemy models
app/schemas/       Request and response validation
app/services/      Authentication and persistence
app/routes/        API endpoints
app/middlewares/   Authentication dependencies
app/utils/         Password hashing and JWT creation
migrations/        Alembic revisions
tests/             API, security, configuration and migration tests
examples/          Archived lessons and experiments; excluded from lint and tests
```

`main.py` remains the server entry point. `database.py` only re-exports the database
objects for compatibility; new code should import `app.database`. Tutorial items
routes are archived in `examples/` rather than exposed in the starter application.
Local databases and `.env` are ignored by Git. `text.txt` is an existing personal
notes file and is not part of the application.

## Before exposing a project publicly

Configure HTTPS, trusted CORS origins and database backups. Enable email
verification, password reset, refresh tokens and authorization policies only when
the project needs them. Do not use the development reload server in production.

## Authentication rate limits

`POST /token` and `POST /register` have independent fixed-window limits per client
IP. Every attempt counts, including successful requests, malformed bodies and
failed logins. Exhausted limits return 429 with a `Retry-After` header in seconds.
Health checks and authenticated profile reads are unaffected. Browser clients can
read `Retry-After` through CORS. The counters store keyed IP digests rather than raw
IP addresses. Rotating the JWT secret changes those digests and resets effective limits.

The default `memory://` backend is for a single local process. Counters reset on
restart and are independent between workers. Before deploying multiple workers or
instances, point all of them to the same Redis service:

```dotenv
RATE_LIMIT_STORAGE_URI=redis://localhost:6379/0
RATE_LIMIT_PREFIX=my-project-production
```

Redis must be provisioned separately; its client is already included in the Python
dependencies. Use a private/authenticated Redis service and `rediss://` when TLS is
required. If the shared backend is unavailable, authentication requests return 503
with `Retry-After: 5`; they do not silently bypass the limit. Redis limits share
counters across processes using the same prefix and signing key. Backend behavior
and supported URLs follow the [limits documentation](https://limits.readthedocs.io/en/stable/storage.html).

The limiter reads the ASGI client address and does not parse forwarding headers.
Uvicorn may update that address from headers of trusted proxies: configure
`--forwarded-allow-ips` with only your reverse proxy's addresses, and prevent direct
access to the application port. Never trust forwarding headers from arbitrary clients.
If you run without a proxy, use `--no-proxy-headers`. Clients sharing a public IP also
share the budget. Fixed windows can permit a burst across a window boundary;
combine this protection with gateway limits for distributed attacks.
