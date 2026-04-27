"""Tests for apps.platform.organizations.services.create_organization."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.common.services import ValidationError
from apps.platform.audit.models import AuditEvent
from apps.platform.organizations.models import Organization
from apps.platform.organizations.services import create_organization
from apps.platform.rbac.models import Role

User = get_user_model()


@pytest.mark.django_db
class TestCreateOrganization:

    def test_creates_org_with_valid_inputs(self):
        org = create_organization(name="Acme Corp", slug="acme")
        assert org.pk is not None
        assert org.name == "Acme Corp"
        assert org.slug == "acme"
        assert org.status == Organization.Status.ACTIVE

    def test_seeds_all_default_roles(self):
        org = create_organization(name="Acme", slug="acme")
        assert Role.objects.for_org(org).count() == 9

    def test_emits_organization_created_audit_event(self):
        user = User.objects.create_user(email="admin@example.com", password="x" * 12)
        org = create_organization(name="Acme", slug="acme", created_by=user)

        events = AuditEvent.objects.filter(event_type="ORGANIZATION_CREATED")
        assert events.count() == 1
        evt = events.get()
        assert evt.actor_user == user
        assert evt.organization == org
        assert evt.after["slug"] == "acme"
        # Summary metadata captures seed result — investigator can see
        # exactly what got provisioned without reading separate events.
        assert evt.metadata["roles_seeded"] == 9

    def test_emits_single_audit_event_not_one_per_role(self):
        # Deliberate design: summary not itemized. Guards against this
        # choice silently drifting into "nine events per org creation."
        create_organization(name="Acme", slug="acme")
        # Only the single ORGANIZATION_CREATED event should exist; the
        # seeding pipeline does not emit per-role events.
        assert AuditEvent.objects.count() == 1

    def test_invalid_slug_raises_validation_error(self):
        # Leading hyphen violates the SlugField validator defined on
        # Organization. Must surface as our domain ValidationError, not
        # Django's raw validation exception.
        with pytest.raises(ValidationError):
            create_organization(name="Bad", slug="-acme")

    def test_duplicate_slug_raises_validation_error(self):
        create_organization(name="First", slug="acme")
        with pytest.raises(ValidationError):
            create_organization(name="Second", slug="acme")

    def test_failure_after_org_create_rolls_back_everything(self, monkeypatch):
        # If role seeding fails (for any reason), the whole transaction
        # rolls back — no org row, no partial roles, no audit event.
        from apps.platform.organizations import services as org_services

        def broken_seed(*args, **kwargs):
            raise RuntimeError("simulated seeding failure")

        monkeypatch.setattr(org_services, "seed_default_roles_for_org", broken_seed)

        with pytest.raises(RuntimeError, match="simulated"):
            create_organization(name="Broken", slug="broken")

        # No org created.
        assert not Organization.objects.filter(slug="broken").exists()
        # No audit event emitted.
        assert not AuditEvent.objects.filter(event_type="ORGANIZATION_CREATED").exists()

    def test_created_by_is_optional(self):
        # System-triggered org creation (fixtures, tests) has no acting user.
        org = create_organization(name="Systemorg", slug="sysorg")
        evt = AuditEvent.objects.filter(event_type="ORGANIZATION_CREATED").get()
        assert evt.actor_user is None
        assert evt.organization == org
