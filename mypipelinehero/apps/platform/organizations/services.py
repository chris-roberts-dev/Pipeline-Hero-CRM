"""
Organizations service layer.

Today: `create_organization` — the canonical way to bring a new tenant into
existence. Handles organization creation, default-role seeding, and audit
event emission as a single atomic operation.

Future additions (org deactivation, slug change, settings update) live in
this module too. Always: plain-Python inputs and outputs, no request
objects, no HTTP concerns.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.common.services import ValidationError
from apps.platform.audit.services import emit as audit_emit
from apps.platform.organizations.models import Organization
from apps.platform.rbac.services import seed_default_roles_for_org


@transaction.atomic
def create_organization(
    *,
    name: str,
    slug: str,
    created_by: Any | None = None,
    **extra_fields,
) -> Organization:
    """Create a new organization and seed its default roles atomically.

    Args:
        name: Human-readable organization name.
        slug: Subdomain segment. Must be unique and pass SlugField/DNS
            validation (see Organization.slug validator).
        created_by: User performing the creation (typically a platform
            admin). Recorded on the AUDIT event. None for system-triggered
            creation (fixtures, tests).
        **extra_fields: Additional Organization fields (status, etc.) for
            the rare caller that needs to override defaults.

    Returns:
        The newly created Organization instance.

    Raises:
        ValidationError: if slug uniqueness fails or field validation
            rejects inputs. DB IntegrityError is caught and re-raised as
            a domain error so callers don't need to know about ORM
            specifics.

    Atomicity:
        Organization creation + role seeding + audit emission all run in a
        single DB transaction. If any step fails, nothing is persisted.
    """
    # Build the Organization instance and validate BEFORE hitting the DB.
    # This surfaces SlugField-level errors as ValidationError rather than
    # as low-level DB constraint violations.
    org = Organization(name=name, slug=slug, **extra_fields)
    try:
        org.full_clean()
    except Exception as exc:
        # Translate Django's ValidationError into our domain error so
        # callers can catch the service-layer contract cleanly.
        raise ValidationError(str(exc)) from exc

    try:
        org.save()
    except Exception as exc:
        # Uniqueness violations end up here. Same rationale as above.
        raise ValidationError(f"Could not create organization: {exc}") from exc

    # Seed the 9 system default roles. This is itself transactional, but
    # we're inside the outer @transaction.atomic, so it runs within our
    # savepoint — if it fails, the org creation rolls back too.
    seed_result = seed_default_roles_for_org(org)

    # Single summary audit event. The alternative — one event per seeded
    # role — would flood the audit log without adding investigative value.
    # The summary payload lets an investigator reconstruct exactly what
    # got seeded without reading nine separate entries.
    audit_emit(
        event_type="ORGANIZATION_CREATED",
        actor_user=created_by,
        organization=org,
        target=("organizations.Organization", org.pk),
        after={
            "name": org.name,
            "slug": org.slug,
            "status": org.status,
        },
        metadata={
            "roles_seeded": seed_result.roles_created,
            "roles_resynced": seed_result.roles_updated,
            "capability_links_created": seed_result.capability_links_created,
        },
    )

    return org
