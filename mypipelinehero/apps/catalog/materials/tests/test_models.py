"""
Tests for RawMaterial model.

Covers:
  - field defaults (is_active)
  - __str__ output (sku and name)
  - unit_of_measure choices accepted; invalid value rejected by full_clean
  - per-org uniqueness on sku
  - cross-org independence (same sku in different orgs)
  - PROTECT semantics on FK delete (organization)
  - MinValueValidator on current_cost (zero allowed, negative rejected)
  - Meta.ordering
  - for_org() tenancy isolation, including chaining with .filter()
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.materials.models import RawMaterial
from apps.platform.organizations.models import Organization


class RawMaterialTestBase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = Organization.objects.create(name="Acme", slug="acme")
        cls.beta = Organization.objects.create(name="Beta", slug="beta")


class RawMaterialTests(RawMaterialTestBase):
    def _make(self, **overrides) -> RawMaterial:
        defaults = dict(
            organization=self.acme,
            sku="STEEL-1",
            name="1/4 inch steel sheet",
            unit_of_measure=RawMaterial.UnitOfMeasure.M2,
            current_cost=Decimal("12.50"),
        )
        defaults.update(overrides)
        return RawMaterial.objects.create(**defaults)

    def test_creates_with_defaults(self) -> None:
        m = self._make()
        self.assertTrue(m.is_active)
        self.assertEqual(m.unit_of_measure, "M2")

    def test_str_includes_sku_and_name(self) -> None:
        m = self._make(sku="ABC", name="Widget")
        self.assertIn("ABC", str(m))
        self.assertIn("Widget", str(m))

    def test_unit_of_measure_choices_accepted(self) -> None:
        # A representative sample across categories.
        for u in [
            RawMaterial.UnitOfMeasure.EACH,
            RawMaterial.UnitOfMeasure.KG,
            RawMaterial.UnitOfMeasure.GAL,
            RawMaterial.UnitOfMeasure.FT,
            RawMaterial.UnitOfMeasure.OTHER,
        ]:
            m = self._make(sku=f"SKU-{u}", unit_of_measure=u)
            self.assertEqual(m.unit_of_measure, u.value)

    def test_invalid_unit_of_measure_rejected_by_full_clean(self) -> None:
        bad = RawMaterial(
            organization=self.acme,
            sku="X",
            name="X",
            unit_of_measure="GARBAGE",
            current_cost=Decimal("1"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_unique_sku_per_org(self) -> None:
        self._make(sku="STEEL-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(sku="STEEL-1")

    def test_same_sku_allowed_in_different_org(self) -> None:
        self._make(sku="STEEL-1")
        beta_steel = RawMaterial.objects.create(
            organization=self.beta,
            sku="STEEL-1",
            name="Beta steel",
            unit_of_measure=RawMaterial.UnitOfMeasure.M2,
            current_cost=Decimal("13.00"),
        )
        self.assertIsNotNone(beta_steel.pk)

    def test_negative_cost_rejected_by_validator(self) -> None:
        bad = RawMaterial(
            organization=self.acme,
            sku="X",
            name="X",
            unit_of_measure=RawMaterial.UnitOfMeasure.EACH,
            current_cost=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_zero_cost_allowed(self) -> None:
        m = self._make(sku="ZERO", current_cost=Decimal("0.00"))
        m.full_clean()
        self.assertEqual(m.current_cost, Decimal("0.00"))

    def test_for_org_tenancy_isolation(self) -> None:
        self._make(sku="A1")
        self._make(sku="A2")
        RawMaterial.objects.create(
            organization=self.beta,
            sku="B1",
            name="B1",
            unit_of_measure=RawMaterial.UnitOfMeasure.EACH,
            current_cost=Decimal("1"),
        )
        self.assertEqual(
            set(RawMaterial.objects.for_org(self.acme).values_list("sku", flat=True)),
            {"A1", "A2"},
        )
        self.assertEqual(
            list(RawMaterial.objects.for_org(self.beta).values_list("sku", flat=True)),
            ["B1"],
        )

    def test_for_org_chains_with_filter(self) -> None:
        self._make(sku="A1", is_active=True)
        self._make(sku="A2", is_active=False)
        active = list(
            RawMaterial.objects.for_org(self.acme)
            .filter(is_active=True)
            .values_list("sku", flat=True)
        )
        self.assertEqual(active, ["A1"])

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    def test_default_ordering_is_name(self) -> None:
        self._make(sku="Z", name="Zebra material")
        self._make(sku="A", name="Apple material")
        names = list(
            RawMaterial.objects.for_org(self.acme).values_list("name", flat=True)
        )
        self.assertEqual(names, ["Apple material", "Zebra material"])
