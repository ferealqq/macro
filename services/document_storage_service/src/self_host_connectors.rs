//! Connector HTTP routes for a self-hosted server.
//!
//! GitHub account linking stays on the authentication service. Slack (and
//! the other MCP connectors) are served by the agent harness in the hosted
//! product. A self-hosted install does not run that process, so document
//! storage mounts the same `/connectors` routes and OAuth callback under
//! `/cognition` when `MACRO_SELF_HOST` is set. The web app already calls
//! that prefix.

use axum::Router;
use connectors::composition::Composed;
use connectors::inbound::axum_router::{ConnectorsRouterState, connectors_router};
use connectors::inbound::callbacks::{CallbacksState, callbacks_router};
use macro_authorization::{MacroAuthorizationService, MacroAuthorizationState};

/// Whether this process should serve connector routes.
pub fn enabled() -> bool {
    matches!(
        std::env::var("MACRO_SELF_HOST")
            .ok()
            .as_deref()
            .map(str::trim),
        Some("1") | Some("true") | Some("TRUE") | Some("yes") | Some("YES")
    )
}

/// `/cognition/connectors` and the public MCP OAuth callback.
pub fn router<Auth>(
    composed: &Composed,
    authorization_state: MacroAuthorizationState<Auth>,
) -> Router
where
    Auth: MacroAuthorizationService,
{
    let connectors_state = ConnectorsRouterState::new(
        composed.connectors.clone(),
        composed.catalog.clone(),
        authorization_state,
    );
    let callbacks_state = CallbacksState::new(composed.sign_ins.clone());
    Router::new().nest(
        "/cognition",
        connectors_router(connectors_state).merge(callbacks_router(callbacks_state)),
    )
}
