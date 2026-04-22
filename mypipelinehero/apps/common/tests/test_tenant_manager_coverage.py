from __future__ import annotations

from django.apps import apps
from django.db import models

from apps.common.tenancy import TenantManager

# Models that legitimately have an `organization` FK but aren't tenant-scoped.
# Keep the reason inline — if you can't articulate why, it shouldn't be here.
EXEMPT: set[str] = {
    # AuditEvent has a nullable `organization` FK because platform-global
    # events (super-admin actions, org creation itself) have no tenant
    # scope. Queries against AuditEvent are always performed with explicit
    # filters at the service layer, not via a default tenant-scoped manager.
    "audit.AuditEvent",
}


def _models_with_organization_fk() -> list[type[models.Model]]:
    """Return every installed model that has a field named `organization`
    which is a ForeignKey to the Organization model."""
    matches: list[type[models.Model]] = []
    for model in apps.get_models():
        # Abstract models don't appear in apps.get_models(), so TenantModel
        # itself isn't checked (good — the abstract base doesn't need a
        # concrete manager attribution).
        try:
            field = model._meta.get_field("organization")
        except Exception:
            continue
        if not isinstance(field, models.ForeignKey):
            continue
        if field.related_model._meta.label != "organizations.Organization":
            continue
        matches.append(model)
    return matches


def test_every_tenant_model_uses_tenant_manager() -> None:
    """Every model with an `organization` FK to organizations.Organization must
    use TenantManager (or a subclass) as its default manager, unless explicitly
    listed in EXEMPT.

    Failure output lists every offender so they can be fixed in one pass.
    """
    offenders: list[str] = []

    for model in _models_with_organization_fk():
        label = model._meta.label
        if label in EXEMPT:
            continue

        default_manager = model._meta.default_manager
        if not isinstance(default_manager, TenantManager):
            # Useful diagnostic: show what manager IS installed, so the author
            # can see at a glance whether they forgot TenantModel entirely,
            # used a plain Manager, or subclassed the wrong base.
            offenders.append(
                f"  {label}: default_manager is {type(default_manager).__name__} "
                f"(must be TenantManager or subclass)"
            )

    if offenders:
        msg = (
            "Tenant-manager coverage violation — the following models have an "
            "`organization` FK but do not use TenantManager as their default "
            "manager. This is a tenancy-isolation risk and must be fixed:\n\n"
            + "\n".join(offenders)
            + "\n\nFix: inherit `apps.common.tenancy.TenantModel`, which sets "
            "`objects = TenantManager()` for you. If this model truly should "
            "be exempt, add it to EXEMPT in this test with a justification."
        )
        raise AssertionError(msg)


def test_exempt_list_only_contains_real_models() -> None:
    """Catch stale entries in EXEMPT — a model that no longer exists or was
    renamed should fail here so the exempt list stays honest."""
    all_labels = {m._meta.label for m in apps.get_models()}
    unknown = EXEMPT - all_labels
    assert not unknown, (
        f"EXEMPT contains labels that don't match any installed model: {unknown}. "
        "Remove stale entries."
    )
