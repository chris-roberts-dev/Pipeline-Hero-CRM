"""Tests for OrganizationAdmin behavior — specifically the save_model
override that routes new-organization creation through the service layer.

Without this override, "Add Organization" in the admin saves the model
directly and skips role seeding + audit emission. The override redirects
to create_organization() so admin-created orgs behave identically to
shell-created or API-created ones.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.platform.audit.models import AuditEvent
from apps.platform.console.admin import OrganizationAdmin
from apps.platform.console.sites import console_site
from apps.platform.organizations.models import Organization
from apps.platform.rbac.models import Role

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@example.com", password="x" * 12)


@pytest.fixture
def request_for(admin_user):
    """A minimal request stand-in. save_model only reads request.user."""

    class FakeRequest:
        user = admin_user

    return FakeRequest()


@pytest.fixture
def org_admin():
    return OrganizationAdmin(Organization, console_site)


@pytest.mark.django_db
class TestOrganizationAdminSaveModel:
    def test_creating_new_org_seeds_default_roles(
        self, org_admin, request_for, admin_user
    ):
        unsaved = Organization(name="Acme Corp", slug="acme")
        org_admin.save_model(request_for, unsaved, form=None, change=False)

        # Org was actually saved.
        assert unsaved.pk is not None
        # The 9 default roles got seeded — proving the service ran.
        assert Role.objects.filter(organization_id=unsaved.pk).count() == 9

    def test_creating_new_org_emits_audit_event(
        self, org_admin, request_for, admin_user
    ):
        unsaved = Organization(name="Acme Corp", slug="acme")
        org_admin.save_model(request_for, unsaved, form=None, change=False)

        # The single ORGANIZATION_CREATED audit event from the service
        # should be present, attributed to the admin user.
        events = AuditEvent.objects.filter(event_type="ORGANIZATION_CREATED")
        assert events.count() == 1
        evt = events.get()
        assert evt.actor_user == admin_user

    def test_editing_existing_org_does_not_reseed(
        self, org_admin, request_for, admin_user
    ):
        # Create via the service (proper flow).
        from apps.platform.organizations.services import create_organization

        org = create_organization(name="Acme Corp", slug="acme")
        roles_before = Role.objects.filter(organization=org).count()
        events_before = AuditEvent.objects.filter(
            event_type="ORGANIZATION_CREATED"
        ).count()

        # Now edit via the admin (change=True).
        org.name = "Acme Inc."
        org_admin.save_model(request_for, org, form=None, change=True)

        org.refresh_from_db()
        assert org.name == "Acme Inc."
        # Role count unchanged — no re-seeding on edit.
        assert Role.objects.filter(organization=org).count() == roles_before
        # No new audit event — seeding's ORGANIZATION_CREATED event is one-shot.
        assert (
            AuditEvent.objects.filter(event_type="ORGANIZATION_CREATED").count()
            == events_before
        )

    def test_invalid_slug_raises_django_validation_error(
        self, org_admin, request_for, admin_user
    ):
        # Leading hyphen violates the SlugField validator.
        from django.core.exceptions import ValidationError as DjValidationError

        unsaved = Organization(name="Bad", slug="-bad-slug")
        with pytest.raises(DjValidationError):
            org_admin.save_model(request_for, unsaved, form=None, change=False)

        # Nothing got persisted.
        assert not Organization.objects.filter(slug="-bad-slug").exists()

    def test_duplicate_slug_raises_django_validation_error(
        self, org_admin, request_for, admin_user
    ):
        from django.core.exceptions import ValidationError as DjValidationError

        Organization.objects.create(name="First", slug="acme")

        unsaved = Organization(name="Second", slug="acme")
        with pytest.raises(DjValidationError):
            org_admin.save_model(request_for, unsaved, form=None, change=False)

        # Original is intact; no duplicate created.
        assert Organization.objects.filter(slug="acme").count() == 1
