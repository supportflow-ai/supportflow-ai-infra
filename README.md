# SupportFlow infrastructure

Owns Compose, NGINX gateway, MinIO build, Jenkins infrastructure and whole-system smoke tests.
Backend owns API/Worker/database Dockerfiles and migrations; frontend owns its Dockerfile.
AI is optional and is not connected in this release.

## Local development

Place the backend, web and this repo beside each other, then:

```sh
cp .env.local.example .env
docker compose -f compose.yaml -f compose.local.yaml up --build -d --wait --wait-timeout 300
docker compose -f compose.yaml -f compose.local.yaml run --rm migrate seed-demo
bash deploy/smoke/smoke-test.sh
```

Set `BACKEND_PATH`/`WEB_PATH` if checkout locations differ. Development configuration
is explicit; plain `compose.yaml` has no credential or image fallback. API ports are
local-only in the development override. Production exposes the gateway only.

Migration and role seeding run as one-shot containers before API/Worker. Demo seeding
is a separate opt-in Development command; it never modifies existing accounts.
Health endpoints: `/health/live`, `/health/ready`, compatible `/health`.

## Production handoff — no automatic deployment

Use `.env.example` and securely supply random credentials and immutable images built
from validated commits. Publish the API/Worker/database images using the same backend
commit. Build MinIO from the included pinned upstream release or supply an approved image.
Run migration using a dedicated schema-owner database credential; configure a separate
runtime credential with only application DML/sequence/function privileges. The local
stack uses one disposable account for convenience and is not the production permission model.

Run `migrate`, `seed-roles` and `check-production` with the database tool before accepting
production traffic. `bootstrap-admin` uses only `BootstrapAdmin__Email` and
`BootstrapAdmin__Password` on the one-shot invocation; do not pass these to API/Worker.
It refuses to elevate an existing account. Reset published demo passwords and review
roles explicitly; no automatic deletion is performed. Rotate a sample JWT key before
production, which invalidates tokens signed with that sample key.

Retain PostgreSQL/MinIO volume contents. This refactor never renumbers tickets or resets
sequences. Before moving an existing stack, preserve its existing physical volumes and
configure Compose external volumes accordingly; never run `down -v` on real data.
Back up and validate upgrades in staging. Roll back application images, not data migrations.

`sources.lock.json` pins CI source commits. To coordinate a backend release, update this
file in a reviewed change. No registry push or production deployment occurs in CI.
Jenkins admin password is required via `JENKINS_ADMIN_PASSWORD`; no default admin secret.
