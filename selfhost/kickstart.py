#!/usr/bin/env python3
"""Write the FusionAuth kickstart for a self-hosted server.

FusionAuth applies this once, against an empty config volume. Secrets come
from the environment written by install.sh. Identifiers match the values the
services expect (see tooling/xtask/.../identity.rs) except the secrets, which
are generated per install.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAMBDA = (
    ROOT
    / "infra/stacks/fusionauth-instance/templates/populate_jwt_local.js"
)
RECONCILE = (
    ROOT
    / "infra/stacks/fusionauth-instance/templates/reconcile_secondary_idp_link.js"
)

APPLICATION_ID = "22222222-2222-4222-8222-222222222222"
TENANT_ID = "11111111-1111-4111-8111-111111111111"
JWT_KEY_ID = "d7d09513-a3f5-401c-9685-34ab6c552453"
LAMBDA_ID = "a7f3e8d2-4b91-4c5a-9e6f-1a2b3c4d5e6f"
TEMPLATE_ID = "33333333-3333-4333-8333-333333333333"
GOOGLE_IDP_ID = "44444444-4444-4444-8444-444444444444"
RECONCILE_ID = "66666666-6666-4666-8666-666666666666"
GITHUB_IDP_ID = "99999999-9999-4999-8999-999999999999"


def load_env() -> None:
    path = Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def real(name: str) -> str:
    """A credential the operator set, rather than an empty or local stub."""
    value = env(name)
    if not value or value.startswith("local-"):
        return ""
    return value


def main() -> None:
    load_env()
    domain = env("DOMAIN", "localhost")
    public = f"https://{domain}"
    api_key = env("FUSIONAUTH_API_KEY")
    jwt_secret = env("JWT_SECRET_KEY")
    client_secret = env("FUSIONAUTH_CLIENT_SECRET_KEY")
    internal = env("INTERNAL_API_SECRET_KEY")
    admin_password = env("FUSIONAUTH_ADMIN_PASSWORD")
    if not all([api_key, jwt_secret, client_secret, internal, admin_password]):
        raise SystemExit("kickstart: missing generated secrets in the environment")

    smtp_host = env("SMTP_HOST", "127.0.0.1")
    smtp_port = int(env("SMTP_PORT", "1025") or "1025")
    smtp_security = env("SMTP_SECURITY", "NONE") or "NONE"
    mail_from = env("SMTP_FROM", "noreply@localhost")

    requests: list[dict] = [
        {
            "method": "POST",
            "url": f"/api/key/import/{JWT_KEY_ID}",
            "body": {
                "key": {
                    "id": JWT_KEY_ID,
                    "algorithm": "HS256",
                    "name": "Self-host JWT signing key",
                    "secret": jwt_secret,
                    "type": "HMAC",
                }
            },
        },
        {
            "method": "POST",
            "url": f"/api/lambda/{LAMBDA_ID}",
            "body": {
                "lambda": {
                    "id": LAMBDA_ID,
                    "name": "Populate JWT (self-host)",
                    "type": "JWTPopulate",
                    "enabled": True,
                    "body": LAMBDA.read_text(),
                }
            },
        },
        {
            "method": "POST",
            "url": f"/api/email/template/{TEMPLATE_ID}",
            "body": {
                "emailTemplate": {
                    "name": "Passwordless login",
                    "defaultSubject": "Your login code",
                    "defaultHtmlTemplate": "<p>Your login code:</p><h1>${code}</h1>",
                    "defaultTextTemplate": "Your login code: ${code}",
                    "fromEmail": mail_from,
                }
            },
        },
        {
            "method": "PATCH",
            "url": f"/api/tenant/{TENANT_ID}",
            "body": {
                "tenant": {
                    "name": "Self-host",
                    "issuer": env("ISSUER", "local.macro.com"),
                    "eventConfiguration": {
                        "events": {
                            "user.create": {
                                "enabled": True,
                                "transactionType": "AbsoluteMajority",
                            },
                            "user.create.complete": {
                                "enabled": True,
                                "transactionType": "None",
                            },
                            "user.delete.complete": {
                                "enabled": True,
                                "transactionType": "None",
                            },
                            "user.email.verified": {
                                "enabled": True,
                                "transactionType": "AbsoluteMajority",
                            },
                        }
                    },
                    "jwtConfiguration": {
                        "accessTokenKeyId": JWT_KEY_ID,
                        "idTokenKeyId": JWT_KEY_ID,
                        "refreshTokenTimeToLiveInMinutes": 43200,
                        "timeToLiveInSeconds": 3600,
                    },
                    "emailConfiguration": {
                        key: value
                        for key, value in {
                            "host": smtp_host,
                            "port": smtp_port,
                            "security": smtp_security,
                            "username": env("SMTP_USERNAME"),
                            "password": env("SMTP_PASSWORD"),
                            "defaultFromEmail": mail_from,
                            "defaultFromName": "Macro",
                            "passwordlessEmailTemplateId": TEMPLATE_ID,
                        }.items()
                        if value != ""
                    },
                    "externalIdentifierConfiguration": {
                        "passwordlessLoginGenerator": {
                            "length": 6,
                            "type": "randomDigits",
                        }
                    },
                }
            },
        },
        {
            "method": "POST",
            "url": f"/api/application/{APPLICATION_ID}",
            "tenantId": TENANT_ID,
            "body": {
                "application": {
                    "name": "Macro",
                    "tenantId": TENANT_ID,
                    "loginConfiguration": {
                        "allowTokenRefresh": True,
                        "requireAuthentication": True,
                        "generateRefreshTokens": True,
                    },
                    "oauthConfiguration": {
                        "clientId": APPLICATION_ID,
                        "clientSecret": client_secret,
                        "enabledGrants": ["authorization_code", "refresh_token"],
                        "authorizedRedirectURLs": [
                            f"{public}/auth/oauth/redirect",
                            f"{public}/app",
                            f"{public}/app/",
                            "http://authentication-service:8080/oauth/redirect",
                        ],
                        "authorizedURLValidationPolicy": "AllowWildcards",
                        "logoutBehavior": "AllApplications",
                        "generateRefreshTokens": True,
                        "requireClientAuthentication": False,
                    },
                    "jwtConfiguration": {
                        "enabled": True,
                        "accessTokenKeyId": JWT_KEY_ID,
                        "idTokenKeyId": JWT_KEY_ID,
                        "timeToLiveInSeconds": 3600,
                        "refreshTokenTimeToLiveInMinutes": 43200,
                        "refreshTokenExpirationPolicy": "SlidingWindow",
                    },
                    "lambdaConfiguration": {"accessTokenPopulateId": LAMBDA_ID},
                    "passwordlessConfiguration": {"enabled": True},
                }
            },
        },
        {
            "method": "POST",
            "url": "/api/user/registration",
            "body": {
                "user": {
                    "email": "admin@localhost",
                    "password": admin_password,
                },
                "registration": {
                    "applicationId": "3c219e58-ed0e-4b18-ad48-f4f92793ae32",
                    "roles": ["admin"],
                },
            },
        },
        {
            "method": "POST",
            "url": "/api/webhook",
            "body": {
                "webhook": {
                    "description": "Create user",
                    "connectTimeout": 1000,
                    "readTimeout": 2000,
                    "url": "http://authentication-service:8080/webhooks/user",
                    "global": True,
                    "eventsEnabled": {
                        "user.create": True,
                        "user.create.complete": True,
                        "user.email.verified": True,
                    },
                    "headers": {"x-internal-auth-key": internal},
                }
            },
        },
        {
            "method": "POST",
            "url": "/api/webhook",
            "body": {
                "webhook": {
                    "description": "Delete user",
                    "connectTimeout": 1000,
                    "readTimeout": 2000,
                    "url": "http://authentication-service:8080/webhooks/user/delete",
                    "global": True,
                    "eventsEnabled": {"user.delete.complete": True},
                    "headers": {"x-internal-auth-key": internal},
                }
            },
        },
    ]

    google_id = real("GOOGLE_CLIENT_ID")
    google_secret = real("GOOGLE_CLIENT_SECRET_KEY")
    if google_id and google_secret:
        oauth = {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth?prompt=consent&access_type=offline",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
            "client_id": google_id,
            "client_secret": google_secret,
            "clientAuthenticationMethod": "client_secret_basic",
            "scope": "openid profile email",
            "uniqueIdClaim": "sub",
            "emailClaim": "email",
            "emailVerifiedClaim": "email_verified",
            "usernameClaim": "preferred_username",
        }
        requests.append(
            {
                "method": "POST",
                "url": f"/api/identity-provider/{GOOGLE_IDP_ID}",
                "body": {
                    "identityProvider": {
                        "type": "OpenIDConnect",
                        "name": "google",
                        "enabled": True,
                        "buttonText": "Google",
                        "linkingStrategy": "LinkByEmail",
                        "oauth2": oauth,
                        "applicationConfiguration": {
                            APPLICATION_ID: {
                                "enabled": True,
                                "createRegistration": True,
                            }
                        },
                    }
                },
            }
        )
        if RECONCILE.exists():
            requests.append(
                {
                    "method": "POST",
                    "url": f"/api/lambda/{RECONCILE_ID}",
                    "body": {
                        "lambda": {
                            "id": RECONCILE_ID,
                            "name": "Reconcile secondary IdP",
                            "type": "OpenIDReconcile",
                            "enabled": True,
                            "body": RECONCILE.read_text(),
                        }
                    },
                }
            )

    github_id = real("GITHUB_CLIENT_ID")
    github_secret = real("GITHUB_CLIENT_SECRET")
    if github_id and github_secret:
        requests.append(
            {
                "method": "POST",
                "url": f"/api/identity-provider/{env('GITHUB_IDP_ID', GITHUB_IDP_ID)}",
                "body": {
                    "identityProvider": {
                        "type": "OpenIDConnect",
                        "name": "github",
                        "enabled": True,
                        "buttonText": "GitHub",
                        "linkingStrategy": "LinkByEmail",
                        "oauth2": {
                            "authorization_endpoint": "https://github.com/login/oauth/authorize",
                            "token_endpoint": "https://github.com/login/oauth/access_token",
                            "userinfo_endpoint": "https://api.github.com/user",
                            "client_id": github_id,
                            "client_secret": github_secret,
                            "clientAuthenticationMethod": "client_secret_basic",
                            "scope": "read:user user:email",
                            "uniqueIdClaim": "id",
                            "emailClaim": "email",
                            "usernameClaim": "login",
                        },
                        "applicationConfiguration": {
                            APPLICATION_ID: {
                                "enabled": True,
                                "createRegistration": True,
                            }
                        },
                    }
                },
            }
        )

    document = {
        "apiKeys": [{"key": api_key, "description": "Self-host API key"}],
        "variables": {"defaultTenantId": TENANT_ID},
        "requests": requests,
    }
    out = Path(__file__).resolve().parent / "generated" / "kickstart.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
