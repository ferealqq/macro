//! Email and password registration for self-hosted deployments.
//!
//! Hosted Macro signs people in with an emailed code. A self-hosted server
//! has no mailbox to read that code from, so `POST /login/signup` creates
//! the account with the password the person chose. The route is absent
//! unless `MACRO_SELF_HOST` is set.

use crate::api::{
    context::ApiContext,
    utils::{create_access_token_cookie, create_refresh_token_cookie},
};
use axum::{
    Json,
    extract::{self, State},
    http::StatusCode,
    response::{IntoResponse, Response},
};
use fusionauth::error::FusionAuthClientError;
use macro_middleware::tracking::ClientIp;
use model::{
    authentication::login::request::PasswordRequest,
    response::{ErrorResponse, UserTokensResponse},
};
use roles_and_permissions::domain::self_host;
use tower_cookies::Cookies;

const MIN_PASSWORD_LEN: usize = 8;
const MAX_PASSWORD_LEN: usize = 200;

/// Creates an account and signs it in.
#[utoipa::path(
    post,
    operation_id = "password_signup",
    path = "/login/signup",
    responses(
        (status = 200, body = UserTokensResponse),
        (status = 400, body = ErrorResponse),
        (status = 403, body = ErrorResponse),
        (status = 404, body = ErrorResponse),
        (status = 409, body = ErrorResponse),
        (status = 500, body = ErrorResponse),
    )
)]
#[tracing::instrument(skip(ctx, req, ip_context), fields(email = %req.email, client_ip = %ip_context), err(Debug))]
pub async fn handler(
    State(ctx): State<ApiContext>,
    ip_context: ClientIp,
    cookies: Cookies,
    extract::Json(req): extract::Json<PasswordRequest>,
) -> Result<Response, Response> {
    if !self_host::enabled() {
        return Err((
            StatusCode::NOT_FOUND,
            Json(ErrorResponse {
                message: "not found".into(),
            }),
        )
            .into_response());
    }

    if !email_validator::is_valid_email(&req.email) {
        return Err(error(StatusCode::BAD_REQUEST, "invalid email"));
    }
    if req.password.len() < MIN_PASSWORD_LEN || req.password.len() > MAX_PASSWORD_LEN {
        return Err(error(
            StatusCode::BAD_REQUEST,
            "password must be 8 to 200 characters",
        ));
    }

    let email = req.email.to_lowercase();
    ctx.signup_policy
        .authorize_public_email(&email)
        .map_err(|_| {
            error(
                StatusCode::FORBIDDEN,
                "signup is not allowed for this address",
            )
        })?;

    ctx.auth_client
        .create_user(
            fusionauth::user::create::User {
                email: (&email).into(),
                password: (&req.password).into(),
                username: None,
                data: None,
            },
            true,
            ip_context.origin_ip(),
        )
        .await
        .map_err(|create_error| match create_error {
            FusionAuthClientError::UserAlreadyExists => error(
                StatusCode::CONFLICT,
                "an account with this email already exists",
            ),
            other => {
                tracing::error!(error = ?other, "unable to create user");
                error(StatusCode::BAD_REQUEST, "unable to create account")
            }
        })?;

    let (access_token, refresh_token) =
        match ctx.auth_client.password_login(&email, &req.password).await {
            Ok(tokens) => tokens,
            Err(FusionAuthClientError::UserNotRegistered) => {
                ctx.auth_client
                    .register_user_from_email(&email)
                    .await
                    .map_err(|register_error| {
                        tracing::error!(error = ?register_error, "unable to register user");
                        error(
                            StatusCode::INTERNAL_SERVER_ERROR,
                            "unable to register account",
                        )
                    })?;
                ctx.auth_client
                    .password_login(&email, &req.password)
                    .await
                    .map_err(|login_error| {
                        tracing::error!(error = ?login_error, "unable to login after signup");
                        error(StatusCode::INTERNAL_SERVER_ERROR, "unable to sign in")
                    })?
            }
            Err(login_error) => {
                tracing::error!(error = ?login_error, "unable to login after signup");
                return Err(error(
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "account was created but sign-in failed",
                ));
            }
        };

    cookies.add(create_access_token_cookie(&access_token));
    cookies.add(create_refresh_token_cookie(&refresh_token));

    Ok((
        StatusCode::OK,
        Json(UserTokensResponse {
            access_token,
            refresh_token,
        }),
    )
        .into_response())
}

fn error(status: StatusCode, message: &str) -> Response {
    (
        status,
        Json(ErrorResponse {
            message: message.into(),
        }),
    )
        .into_response()
}
