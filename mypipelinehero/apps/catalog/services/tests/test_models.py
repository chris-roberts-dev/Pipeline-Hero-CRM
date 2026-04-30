"""
Tests for ServiceCategory and Service models.

Covers:
  - field defaults (is_active, description)
  - __str__ output
  - per-org uniqueness on code
  - cross-org independence (same code allowed in different orgs)
  - PROTECT semantics on FK deletes (organization, category)
  - MinValueValidator on Service.catalog_price
  - Meta.ordering
  - for_org() tenancy isolation, including chaining with .filter()
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.services.models import Service, ServiceCategory
from apps.platform.organizations.models import Organization


class CatalogServicesTestBase(TestCase):
    """Common fixture: two orgs so cross-tenant tests have something to compare."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = Organization.objects.create(name="Acme", slug="acme")
        cls.beta = Organization.objects.create(name="Beta", slug="beta")


class ServiceCategoryTests(CatalogServicesTestBase):
    def test_creates_with_defaults(self) -> None:
        cat = ServiceCategory.objects.create(
            organization=self.acme, code="PLUMB", name="Plumbing"
        )
        self.assertTrue(cat.is_active)
        self.assertIsNotNone(cat.created_at)
        self.assertIsNotNone(cat.updated_at)

    def test_str_returns_name(self) -> None:
        cat = ServiceCategory.objects.create(
            organization=self.acme, code="PLUMB", name="Plumbing"
        )
        self.assertEqual(str(cat), "Plumbing")

    def test_unique_code_per_org(self) -> None:
        ServiceCategory.objects.create(
            organization=self.acme, code="PLUMB", name="Plumbing"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ServiceCategory.objects.create(
                organization=self.acme, code="PLUMB", name="Dupe"
            )

    def test_same_code_allowed_in_different_org(self) -> None:
        ServiceCategory.objects.create(
            organization=self.acme, code="PLUMB", name="Acme Plumbing"
        )
        # Should not raise.
        beta_cat = ServiceCategory.objects.create(
            organization=self.beta, code="PLUMB", name="Beta Plumbing"
        )
        self.assertIsNotNone(beta_cat.pk)

    def test_for_org_tenancy_isolation(self) -> None:
        ServiceCategory.objects.create(organization=self.acme, code="A1", name="A1")
        ServiceCategory.objects.create(organization=self.acme, code="A2", name="A2")
        ServiceCategory.objects.create(organization=self.beta, code="B1", name="B1")
        self.assertEqual(
            set(
                ServiceCategory.objects.for_org(self.acme).values_list(
                    "code", flat=True
                )
            ),
            {"A1", "A2"},
        )
        self.assertEqual(
            list(
                ServiceCategory.objects.for_org(self.beta).values_list(
                    "code", flat=True
                )
            ),
            ["B1"],
        )

    def test_organization_delete_protected(self) -> None:
        ServiceCategory.objects.create(organization=self.acme, code="X", name="X")
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    def test_default_ordering_is_name(self) -> None:
        ServiceCategory.objects.create(organization=self.acme, code="Z", name="Zebra")
        ServiceCategory.objects.create(organization=self.acme, code="A", name="Apple")
        names = list(
            ServiceCategory.objects.for_org(self.acme).values_list("name", flat=True)
        )
        self.assertEqual(names, ["Apple", "Zebra"])


class ServiceTests(CatalogServicesTestBase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.acme_cat = ServiceCategory.objects.create(
            organization=cls.acme, code="PLUMB", name="Plumbing"
        )
        cls.beta_cat = ServiceCategory.objects.create(
            organization=cls.beta, code="PLUMB", name="Beta Plumbing"
        )

    def _make(self, **overrides) -> Service:
        defaults = dict(
            organization=self.acme,
            category=self.acme_cat,
            code="DRAIN",
            name="Drain cleaning",
            catalog_price=Decimal("199.00"),
        )
        defaults.update(overrides)
        return Service.objects.create(**defaults)

    def test_creates_with_defaults(self) -> None:
        svc = self._make()
        self.assertTrue(svc.is_active)
        self.assertEqual(svc.description, "")

    def test_str_returns_name(self) -> None:
        self.assertEqual(str(self._make(name="Snake")), "Snake")

    def test_unique_code_per_org(self) -> None:
        self._make(code="DRAIN")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(code="DRAIN")

    def test_same_code_allowed_in_different_org(self) -> None:
        self._make(code="DRAIN")
        # Should not raise.
        beta_svc = Service.objects.create(
            organization=self.beta,
            category=self.beta_cat,
            code="DRAIN",
            name="Beta drain",
            catalog_price=Decimal("99.00"),
        )
        self.assertIsNotNone(beta_svc.pk)

    def test_negative_price_rejected_by_validator(self) -> None:
        bad = Service(
            organization=self.acme,
            category=self.acme_cat,
            code="X",
            name="X",
            catalog_price=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_zero_price_allowed(self) -> None:
        svc = self._make(code="ZERO", catalog_price=Decimal("0.00"))
        svc.full_clean()  # should not raise
        self.assertEqual(svc.catalog_price, Decimal("0.00"))

    def test_category_delete_protected_when_referenced(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme_cat.delete()

    def test_empty_category_can_be_deleted(self) -> None:
        empty = ServiceCategory.objects.create(
            organization=self.acme, code="EMPTY", name="Empty"
        )
        empty.delete()
        self.assertFalse(ServiceCategory.objects.filter(pk=empty.pk).exists())

    def test_for_org_tenancy_isolation(self) -> None:
        self._make(code="A1")
        Service.objects.create(
            organization=self.beta,
            category=self.beta_cat,
            code="B1",
            name="B1",
            catalog_price=Decimal("1"),
        )
        self.assertEqual(
            list(Service.objects.for_org(self.acme).values_list("code", flat=True)),
            ["A1"],
        )
        self.assertEqual(
            list(Service.objects.for_org(self.beta).values_list("code", flat=True)),
            ["B1"],
        )

    def test_for_org_chains_with_filter(self) -> None:
        self._make(code="A1", is_active=True)
        self._make(code="A2", is_active=False)
        active = list(
            Service.objects.for_org(self.acme)
            .filter(is_active=True)
            .values_list("code", flat=True)
        )
        self.assertEqual(active, ["A1"])

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    def test_default_ordering_is_name(self) -> None:
        Service.objects.create(
            organization=self.acme,
            category=self.acme_cat,
            code="Z",
            name="Zebra service",
            catalog_price=Decimal("1"),
        )
        Service.objects.create(
            organization=self.acme,
            category=self.acme_cat,
            code="A",
            name="Apple service",
            catalog_price=Decimal("1"),
        )
        names = list(Service.objects.for_org(self.acme).values_list("name", flat=True))
        self.assertEqual(names, ["Apple service", "Zebra service"])
