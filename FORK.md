# Fork divergences

This checkout is a long-lived fork. Upstream stays the source of product
behavior. Self-hosting is a flag and a `selfhost/` directory, not a delete
of the hosted product.

When merging upstream, keep this file current. Search for `MACRO_SELF_HOST`
and `VITE_SELF_HOST` after the merge. If a new plan check appears, route it
through the same flag. If a new required env var appears, add it to
`selfhost/.env.example` with a local stub.

## Flag

`MACRO_SELF_HOST=true` on the services. `VITE_SELF_HOST=true` is inlined
into the self-host web bundle (`selfhost/Dockerfile.frontend`).

What it changes:

| Place | Effect |
| --- | --- |
| `crates/roles_and_permissions/src/domain/self_host.rs` | Roles and permissions include the paid subscriber role, the Max tier role, and `read:professional_features`, `write:ai_features`, `write:proai`. Read once per process. |
| `crates/macro_db_client/src/user/get_permissions.rs` | The same permission strings. The license endpoint reads this query and does not call the roles service. |
| `crates/ai_billing/src/outbound/entitlement.rs` | The entitlement is an unlimited Max seat. Stripe is not consulted. `ENABLE_AI_USAGE_ENFORCEMENT` and `ENABLE_AI_USAGE_BILLING` stay off in `.env.example`. |
| `services/authentication_service` `POST /login/signup` | Creates an email-and-password account. The route is 404 when the flag is off. |
| `services/document_storage_service/src/self_host_connectors.rs` | Mounts `/cognition/connectors` and the MCP OAuth callback so Slack connect does not need the agent service. |
| `apps/web` `selfHost` flag | Hides mail, chat, calendar, calls, CRM, agents, and the matching settings tabs. Integrations shows GitHub and Slack. Paywall does not open. Paid access is true. Sign-in asks for a password and creates the account if it is new. Google is hidden until `/selfhost.json` says otherwise. Onboarding is skipped. Service hosts are the same-origin proxy even though the bundle is a production build. |

`ENVIRONMENT=local` in the self-host env is required for a second reason:
cookies are host-only (a production environment would pin them to
`macro.com`) and secret env vars are the secret itself, not an AWS Secrets
Manager name. That is a deployment setting, not a second product flag.

## Deployment

`selfhost/` is new. It does not replace `docker/`, `just run_local`, or the
Pulumi stacks. Those still build the hosted product and the developer
stack.

The image build workflow lives at `selfhost/ci/build-images.yml` and is
not generated into `.github/workflows`. Adding it there without a module
in `tooling/xtask/crates/xtask_workflows` fails `cargo x workflows
--check`. Register it there if GitHub should publish the images.

## Not removed

Email, calendar, CRM, calls, and the agent service are still in the tree.
They are not in the self-host compose file, and Caddy answers their paths
with 503. Deleting them would make every upstream merge a conflict.

LocalStack stands in for S3, SQS, DynamoDB, and KMS. Replacing it with
MinIO and a queue that is not AWS-shaped means teaching every client to
use a different endpoint per service. That is not done. `localstack/init.sh`
recreates the resources on each boot because the community image does not
keep them.

OpenSearch is still required for document storage to pass its startup
health check. Kafka is still started because document storage publishes
events. Both are memory-capped in the compose file.

## Merging upstream

1. Merge the upstream branch.
2. Resolve conflicts in the files in the table above. Prefer keeping the
   `MACRO_SELF_HOST` branch and taking upstream's other changes.
3. If a new service is required for docs, tasks, GitHub, or Slack, add it
   to `selfhost/docker-compose.yml` and `.env.example`.
4. If sign-in or the connector routes move, update `selfhost/Caddyfile`
   and `selfhost/integrations/README.md`.
5. Run `selfhost/upgrade.sh <host>` on a test machine. Do not point it at
   a hosted environment.
