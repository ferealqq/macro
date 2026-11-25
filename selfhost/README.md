# Self-hosted Macro

Docs, tasks, and the GitHub and Slack connect flows, with every account on
the Max plan. Email, calendar, calls, CRM, and the agent service are not in
this stack. Billing and Stripe are not contacted.

The flag is `MACRO_SELF_HOST` (services) and `VITE_SELF_HOST` (the web
bundle). Hosted builds leave both unset.

## Install

On the server, from a checkout of this fork:

```sh
selfhost/install.sh your-host.example
```

Use `localhost` when you are opening the machine directly. The script
generates `.env` and `credentials.txt` (mode 600), writes the FusionAuth
kickstart, builds the images, migrates Postgres, and starts the stack.

Open `https://<host>/app/`. The first email and password (8 or more
characters) creates the account. There is no emailed code and nothing is
filled in for you.

`selfhost/upgrade.sh` rebuilds from the current checkout and migrates.
It keeps volumes and `.env`.

Images can be built by the workflow in `selfhost/ci/build-images.yml`. It
is not registered under `.github/workflows`, because those files are
generated and a hand-written one fails the workflow check. To pull instead
of building, set `IMAGE_PREFIX` and `IMAGE_TAG` in the environment before
`docker compose up`. See `FORK.md`.

## What is running

| Container | Role |
| --- | --- |
| proxy | Caddy, the web bundle, TLS |
| authentication-service | Sign-in, GitHub account link |
| document-storage-service | Docs, tasks, Slack connect |
| sync-service, lexical-service | Collaborative document text |
| connection-gateway | Live updates |
| static-file-service, document-upload-finalizer | Files and uploads |
| postgres | App data and FusionAuth |
| redis, kafka, search | Cache, events, full-text search |
| localstack | S3, SQS, DynamoDB, and KMS stand-ins |
| fusionauth | Identity store |

Caddy answers `/email`, `/calendar`, `/notification`, `/contacts`, and the
agent paths with 503. Those screens are hidden in the bundle.

## Memory

Sized for a 2 vCPU machine with 3.8 GB of RAM and swap. Compose sets a
limit on each container: Postgres 512 MB, OpenSearch 512 MB, LocalStack
512 MB, FusionAuth 420 MB, Kafka 384 MB, document storage 640 MB, the other
Rust processes 384 MB, sync and lexical 256 MB, Redis 96 MB, Caddy 128 MB.
The limits sum above 3.8 GB; the processes stay under their limits, and the
measurement for a booted stack is in the pull request. OpenSearch is the
one to shrink first (`OPENSEARCH_JAVA_OPTS` on the `search` service) if the
machine starts swapping hard.

LocalStack community edition rebuilds buckets, queues, and tables on every
boot (`localstack/init.sh`). Document text is in Postgres and the sync
volume. Uploaded file bytes in the object store are not part of that
restore.

## GitHub, Slack, Google, SMTP

`integrations/README.md`. Placeholders are enough for the buttons to reach
GitHub and Slack. The providers reject them until you replace the client
ids and secrets.

## Layout

| Path | Purpose |
| --- | --- |
| `docker-compose.yml` | The stack |
| `Dockerfile.services` | The Rust binaries |
| `Dockerfile.frontend` | The web bundle and Caddy |
| `Caddyfile` | Routes |
| `.env.example` | Every variable, with tokens install.sh replaces |
| `install.sh`, `upgrade.sh` | First boot and later boots |
| `kickstart.py` | FusionAuth, including optional Google and GitHub providers |
| `migrate.py` | MacroDB migrations |
| `integrations/` | GitHub and Slack setup, Slack manifest |
