# GitHub and Slack for a self-hosted server

Replace `DOMAIN` with the host in `.env` (the name that points at this
server). Create the apps, put the values in
`.env`, then `docker compose up -d` from `selfhost/`. The GitHub identity
provider is created only on FusionAuth's first boot. If you change
`GITHUB_CLIENT_ID` after that, recreate the `fusionauth` volume (this drops
FusionAuth users) or add the provider in the FusionAuth admin console.

The connect buttons redirect to GitHub and Slack even with the placeholder
client ids. Those providers reject the placeholder. That is the expected
result until the values below are real.

## GitHub account link (OAuth app)

Create a GitHub OAuth app. Homepage URL `https://DOMAIN`. Authorization
callback URL:

`https://DOMAIN/auth/oauth2/github/callback`

The account-link request asks for the `repo` and `user:email` scopes.

| Value | Env |
| --- | --- |
| Client ID | `GITHUB_CLIENT_ID` |
| Client secret | `GITHUB_CLIENT_SECRET` |

`GITHUB_IDP_ID` stays `99999999-9999-4999-8999-999999999999` unless you
created the FusionAuth provider under another id.

In the app: Settings → Integrations → GitHub. The browser goes to
`https://github.com/login/oauth/authorize`.

## GitHub App (repository install and webhooks)

Create a GitHub App. Homepage `https://DOMAIN`. Setup URL (post
installation):

`https://DOMAIN/dss/github/sync-redirect`

Webhook URL:

`https://DOMAIN/dss/github/webhook`

Webhook secret: the value you put in `GITHUB_WEBHOOK_SECRET_KEY`.

Permissions (read), matching `crates/github/app-webhooks.json`:

`actions`, `checks`, `contents`, `deployments`, `discussions`, `issues`,
`merge_queues`, `metadata`, `pull_requests`, `statuses`.

Subscribe to the events listed in that file (`push`, `pull_request`,
`issues`, `workflow_run`, and the rest of `default_events`).
`installation` and `installation_repositories` arrive without a checkbox.

| Value | Env |
| --- | --- |
| `https://github.com/apps/<slug>` | `GITHUB_SYNC_APP_URL` |
| App client id | `GITHUB_SYNC_APP_CLIENT_ID` |
| App client secret | `GITHUB_SYNC_APP_CLIENT_SECRET` |
| PEM of the app private key, the text of the `.pem` file | `GITHUB_SYNC_APP_PEM_SECRET_KEY` |
| Webhook secret | `GITHUB_WEBHOOK_SECRET_KEY` |
| Any random string of 32 or more characters | `GITHUB_INSTALLATION_STATE_SECRET` |

The install button opens `https://DOMAIN/dss/github/install-sync`, which
redirects to the app's install page.

A PEM in `.env` must be one line with literal `\n` sequences, or the
service will not parse it. Generating the install redirect does not read
the PEM. Processing webhooks does.

## Slack

Create a Slack app from `slack-manifest.json` in this directory. Replace
`DOMAIN` in the redirect URL first:

`https://DOMAIN/cognition/mcp/servers/auth/callback`

The manifest turns on Slack's MCP integration and the user scopes Macro
requests. It does not subscribe to the Events API.

| Value | Env |
| --- | --- |
| Client ID | `SLACK_MCP_CLIENT_ID` |
| Client secret | `SLACK_MCP_CLIENT_SECRET` |

In the app: Settings → Integrations → Slack. The browser goes to Slack's
authorize page. The callback is served by document storage under
`/cognition`, which is the path the hosted agent service uses.

## Google sign-in (optional)

In Google Cloud, an OAuth web client. Authorized redirect URI:

`https://DOMAIN/oauth2/callback`

| Value | Env |
| --- | --- |
| Client ID | `GOOGLE_CLIENT_ID` |
| Client secret | `GOOGLE_CLIENT_SECRET_KEY` |
| `true` | `SELFHOST_GOOGLE` |

Then recreate the FusionAuth volume so the kickstart creates the `google`
identity provider. Until then the Google button stays hidden
(`GET /selfhost.json`).

## Email codes (optional)

Password sign-in does not send mail. To also send the six-digit code, set
`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY` (`NONE` or `TLS`), and
`SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM` when the server requires
them. Recreate the FusionAuth volume so the tenant picks up the host.
The web app does not fill the code in for you.
