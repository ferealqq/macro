//! Self-hosted deployments treat every account as Max.
//!
//! `MACRO_SELF_HOST` is the one switch. It is read once per process. Hosted
//! environments leave it unset. The same variable is also read by the SQL
//! permission lookup in `macro_db_client`, which does not call this module.

use std::collections::HashSet;
use std::sync::OnceLock;

use super::model::{PermissionId, RoleId};

/// Whether this process is the self-hosted product.
pub fn enabled() -> bool {
    static ENABLED: OnceLock<bool> = OnceLock::new();
    *ENABLED.get_or_init(|| {
        matches!(
            std::env::var("MACRO_SELF_HOST")
                .ok()
                .as_deref()
                .map(str::trim),
            Some("1") | Some("true") | Some("TRUE") | Some("yes") | Some("YES")
        )
    })
}

/// Grant the paid subscriber role and the Max tier role.
pub fn augment_roles(roles: &mut HashSet<RoleId>) {
    roles.insert(RoleId::ProfessionalSubscriber);
    roles.insert(RoleId::SubMax);
}

/// Grant the permissions those roles carry in the database.
pub fn augment_permissions(permissions: &mut HashSet<PermissionId>) {
    permissions.insert(PermissionId::ReadProfessionalFeatures);
    permissions.insert(PermissionId::WriteAiFeatures);
    permissions.insert(PermissionId::WriteProAi);
}

#[cfg(test)]
mod test {
    use super::*;

    #[test]
    fn augment_roles_adds_the_paid_and_max_roles() {
        let mut roles = HashSet::new();
        augment_roles(&mut roles);
        assert!(roles.contains(&RoleId::ProfessionalSubscriber));
        assert!(roles.contains(&RoleId::SubMax));
    }

    #[test]
    fn augment_permissions_adds_the_paid_permissions() {
        let mut permissions = HashSet::new();
        augment_permissions(&mut permissions);
        assert!(permissions.contains(&PermissionId::ReadProfessionalFeatures));
        assert!(permissions.contains(&PermissionId::WriteProAi));
        assert!(permissions.contains(&PermissionId::WriteAiFeatures));
    }
}
