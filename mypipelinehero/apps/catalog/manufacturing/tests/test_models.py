"""
Tests for BOM and BOMLine models.

BOM:
  - field defaults (status defaults to DRAFT)
  - __str__ output
  - per-(org, product, version) uniqueness on version label
  - cross-org independence
  - status TextChoices: DRAFT/ACTIVE/SUPERSEDED accepted; invalid rejected
  - PROTECT on organization, finished_product
  - **Active uniqueness**: at most one ACTIVE BOM per finished_product;
    multiple DRAFT and multiple SUPERSEDED rows are allowed
  - clean(): ACTIVE/SUPERSEDED BOMs cannot have future effective_from;
    DRAFT may have any date
  - default ordering by (finished_product, -effective_from, -version)
  - for_org() tenancy isolation

BOMLine:
  - quantity / cost_basis_quantity validators (≥0)
  - cost_reference validator (≥0)
  - unit_of_measure must come from RawMaterial.UnitOfMeasure choices
  - per-BOM uniqueness on raw_material (each material appears once per BOM)
  - CASCADE on bom (deleting a BOM removes lines)
  - PROTECT on raw_material (cannot delete a raw material referenced by any line)
  - PROTECT on organization
  - __str__ shows quantity, UoM, raw material name
  - default ordering within a BOM is by raw_material name
  - for_org() tenancy isolation

Tests run against Postgres — partial unique indexes and the workflow
constraints are Postgres-native and would be unreliable on SQLite.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.manufacturing.models import BOM, BOMLine
from apps.catalog.materials.models import RawMaterial
from apps.catalog.products.models import Product
from apps.platform.organizations.models import Organization


class ManufacturingTestBase(TestCase):
    """Common fixture: two orgs, a manufactured product per org, a few materials."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = Organization.objects.create(name="Acme", slug="acme")
        cls.beta = Organization.objects.create(name="Beta", slug="beta")
        cls.acme_widget = Product.objects.create(
            organization=cls.acme,
            product_type=Product.ProductType.MANUFACTURED,
            sku="WIDGET-MFG",
            name="Widget (manufactured)",
        )
        cls.beta_widget = Product.objects.create(
            organization=cls.beta,
            product_type=Product.ProductType.MANUFACTURED,
            sku="WIDGET-MFG",
            name="Beta widget",
        )
        cls.acme_steel = RawMaterial.objects.create(
            organization=cls.acme,
            sku="STEEL-1",
            name="Steel sheet",
            unit_of_measure=RawMaterial.UnitOfMeasure.M2,
            current_cost=Decimal("10.00"),
        )
        cls.acme_paint = RawMaterial.objects.create(
            organization=cls.acme,
            sku="PAINT-1",
            name="Red paint",
            unit_of_measure=RawMaterial.UnitOfMeasure.L,
            current_cost=Decimal("5.00"),
        )


# ---------------------------------------------------------------------------
# BOM
# ---------------------------------------------------------------------------


class BOMTests(ManufacturingTestBase):
    def _make(self, **overrides) -> BOM:
        defaults = dict(
            organization=self.acme,
            finished_product=self.acme_widget,
            version="v1",
            effective_from=datetime.date(2025, 1, 1),
        )
        defaults.update(overrides)
        return BOM.objects.create(**defaults)

    def test_creates_with_defaults(self) -> None:
        bom = self._make()
        self.assertEqual(bom.status, "DRAFT")

    def test_str_includes_version_product_status(self) -> None:
        bom = self._make(version="v2.1")
        s = str(bom)
        self.assertIn("v2.1", s)
        self.assertIn(self.acme_widget.name, s)
        self.assertIn("DRAFT", s)

    def test_status_choices_accepted(self) -> None:
        # All three statuses can be saved at the DB level.
        for status in [BOM.Status.DRAFT, BOM.Status.ACTIVE, BOM.Status.SUPERSEDED]:
            bom = self._make(version=f"v-{status}", status=status)
            self.assertEqual(bom.status, status.value)

    def test_invalid_status_rejected_by_full_clean(self) -> None:
        bad = BOM(
            organization=self.acme,
            finished_product=self.acme_widget,
            version="v1",
            effective_from=datetime.date(2025, 1, 1),
            status="GARBAGE",
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_unique_version_per_org_and_product(self) -> None:
        self._make(version="v1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(version="v1")

    def test_same_version_allowed_for_different_product(self) -> None:
        # Same org but a different finished_product: version label can repeat.
        other_product = Product.objects.create(
            organization=self.acme,
            product_type=Product.ProductType.MANUFACTURED,
            sku="GADGET-MFG",
            name="Gadget",
        )
        self._make(version="v1")
        # Should not raise.
        bom = BOM.objects.create(
            organization=self.acme,
            finished_product=other_product,
            version="v1",
            effective_from=datetime.date(2025, 1, 1),
        )
        self.assertIsNotNone(bom.pk)

    def test_same_version_allowed_in_different_org(self) -> None:
        self._make(version="v1")
        # Same version label, different org — must be allowed.
        bom = BOM.objects.create(
            organization=self.beta,
            finished_product=self.beta_widget,
            version="v1",
            effective_from=datetime.date(2025, 1, 1),
        )
        self.assertIsNotNone(bom.pk)

    # --- The active-uniqueness partial index --------------------------------

    def test_only_one_active_bom_per_finished_product(self) -> None:
        self._make(version="v1", status=BOM.Status.ACTIVE)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(version="v2", status=BOM.Status.ACTIVE)

    def test_multiple_draft_boms_allowed(self) -> None:
        # Many DRAFTs can coexist for the same product — the partial unique
        # index has WHERE status='ACTIVE', so DRAFTs aren't constrained.
        self._make(version="v1", status=BOM.Status.DRAFT)
        self._make(version="v2", status=BOM.Status.DRAFT)
        self._make(version="v3", status=BOM.Status.DRAFT)
        self.assertEqual(
            BOM.objects.for_org(self.acme).filter(status=BOM.Status.DRAFT).count(),
            3,
        )

    def test_multiple_superseded_boms_allowed(self) -> None:
        # Likewise SUPERSEDED — historical revisions accumulate freely.
        self._make(version="v1", status=BOM.Status.SUPERSEDED)
        self._make(version="v2", status=BOM.Status.SUPERSEDED)
        self.assertEqual(
            BOM.objects.for_org(self.acme).filter(status=BOM.Status.SUPERSEDED).count(),
            2,
        )

    def test_active_uniqueness_is_per_finished_product(self) -> None:
        # Two MANUFACTURED products, each can have its own ACTIVE BOM.
        other_product = Product.objects.create(
            organization=self.acme,
            product_type=Product.ProductType.MANUFACTURED,
            sku="GADGET-MFG",
            name="Gadget",
        )
        self._make(version="v1", status=BOM.Status.ACTIVE)
        bom2 = BOM.objects.create(
            organization=self.acme,
            finished_product=other_product,
            version="v1",
            effective_from=datetime.date(2025, 1, 1),
            status=BOM.Status.ACTIVE,
        )
        self.assertIsNotNone(bom2.pk)

    def test_active_uniqueness_is_per_organization(self) -> None:
        # Both orgs can have an ACTIVE BOM for their respective WIDGET-MFG.
        self._make(version="v1", status=BOM.Status.ACTIVE)
        beta_bom = BOM.objects.create(
            organization=self.beta,
            finished_product=self.beta_widget,
            version="v1",
            effective_from=datetime.date(2025, 1, 1),
            status=BOM.Status.ACTIVE,
        )
        self.assertIsNotNone(beta_bom.pk)

    # --- clean() workflow validation ----------------------------------------

    def test_active_bom_cannot_have_future_effective_from(self) -> None:
        future = datetime.date(2099, 1, 1)
        bom = BOM(
            organization=self.acme,
            finished_product=self.acme_widget,
            version="v1",
            effective_from=future,
            status=BOM.Status.ACTIVE,
        )
        with self.assertRaises(ValidationError) as ctx:
            bom.full_clean()
        self.assertIn("effective_from", ctx.exception.message_dict)

    def test_superseded_bom_cannot_have_future_effective_from(self) -> None:
        future = datetime.date(2099, 1, 1)
        bom = BOM(
            organization=self.acme,
            finished_product=self.acme_widget,
            version="v1",
            effective_from=future,
            status=BOM.Status.SUPERSEDED,
        )
        with self.assertRaises(ValidationError):
            bom.full_clean()

    def test_draft_bom_can_have_future_effective_from(self) -> None:
        future = datetime.date(2099, 1, 1)
        bom = BOM(
            organization=self.acme,
            finished_product=self.acme_widget,
            version="v-future",
            effective_from=future,
            status=BOM.Status.DRAFT,
        )
        # Should NOT raise — DRAFT may plan future revisions.
        bom.full_clean()

    def test_active_bom_with_today_effective_from_is_valid(self) -> None:
        from django.utils import timezone

        today = timezone.localdate()
        bom = BOM(
            organization=self.acme,
            finished_product=self.acme_widget,
            version="v-today",
            effective_from=today,
            status=BOM.Status.ACTIVE,
        )
        bom.full_clean()  # should not raise

    # --- PROTECT semantics --------------------------------------------------

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    def test_finished_product_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme_widget.delete()

    # --- Tenancy ------------------------------------------------------------

    def test_for_org_tenancy_isolation(self) -> None:
        self._make(version="acme-1")
        BOM.objects.create(
            organization=self.beta,
            finished_product=self.beta_widget,
            version="beta-1",
            effective_from=datetime.date(2025, 1, 1),
        )
        self.assertEqual(
            list(BOM.objects.for_org(self.acme).values_list("version", flat=True)),
            ["acme-1"],
        )
        self.assertEqual(
            list(BOM.objects.for_org(self.beta).values_list("version", flat=True)),
            ["beta-1"],
        )

    def test_default_ordering_recent_first(self) -> None:
        # ordering = ("finished_product", "-effective_from", "-version")
        self._make(version="v1", effective_from=datetime.date(2025, 1, 1))
        self._make(version="v2", effective_from=datetime.date(2025, 6, 1))
        self._make(version="v3", effective_from=datetime.date(2025, 3, 1))
        versions = list(
            BOM.objects.for_org(self.acme).values_list("version", flat=True)
        )
        # Sorted by effective_from desc: v2 (June), v3 (March), v1 (January).
        self.assertEqual(versions, ["v2", "v3", "v1"])


# ---------------------------------------------------------------------------
# BOMLine
# ---------------------------------------------------------------------------


class BOMLineTests(ManufacturingTestBase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.bom = BOM.objects.create(
            organization=cls.acme,
            finished_product=cls.acme_widget,
            version="v1",
            effective_from=datetime.date(2025, 1, 1),
        )

    def _make(self, **overrides) -> BOMLine:
        defaults = dict(
            organization=self.acme,
            bom=self.bom,
            raw_material=self.acme_steel,
            quantity=Decimal("3.0000"),
            unit_of_measure=RawMaterial.UnitOfMeasure.KG,
            cost_basis_quantity=Decimal("0.2500"),
            cost_reference=Decimal("10.00"),
        )
        defaults.update(overrides)
        return BOMLine.objects.create(**defaults)

    def test_creates_with_dual_quantities(self) -> None:
        line = self._make()
        # Display side
        self.assertEqual(line.quantity, Decimal("3.0000"))
        self.assertEqual(line.unit_of_measure, "KG")
        # Cost-basis side
        self.assertEqual(line.cost_basis_quantity, Decimal("0.2500"))
        self.assertEqual(line.cost_reference, Decimal("10.00"))

    def test_str_includes_quantity_uom_and_material(self) -> None:
        line = self._make()
        s = str(line)
        self.assertIn("3.0000", s)
        self.assertIn("KG", s)
        self.assertIn("Steel sheet", s)

    def test_negative_quantity_rejected_by_validator(self) -> None:
        bad = BOMLine(
            organization=self.acme,
            bom=self.bom,
            raw_material=self.acme_steel,
            quantity=Decimal("-1.0000"),
            unit_of_measure=RawMaterial.UnitOfMeasure.KG,
            cost_basis_quantity=Decimal("0.2500"),
            cost_reference=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_negative_cost_basis_quantity_rejected_by_validator(self) -> None:
        bad = BOMLine(
            organization=self.acme,
            bom=self.bom,
            raw_material=self.acme_steel,
            quantity=Decimal("1.0000"),
            unit_of_measure=RawMaterial.UnitOfMeasure.KG,
            cost_basis_quantity=Decimal("-0.2500"),
            cost_reference=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_negative_cost_reference_rejected_by_validator(self) -> None:
        bad = BOMLine(
            organization=self.acme,
            bom=self.bom,
            raw_material=self.acme_steel,
            quantity=Decimal("1.0000"),
            unit_of_measure=RawMaterial.UnitOfMeasure.KG,
            cost_basis_quantity=Decimal("0.2500"),
            cost_reference=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_zero_quantities_allowed(self) -> None:
        # Edge case: a "placeholder" line with zero values, e.g. before the
        # user has filled in actuals. Positive validators allow zero.
        line = self._make(
            quantity=Decimal("0"),
            cost_basis_quantity=Decimal("0"),
            cost_reference=Decimal("0"),
        )
        line.full_clean()
        self.assertEqual(line.quantity, Decimal("0"))

    def test_unit_of_measure_choices_accepted(self) -> None:
        # BOMLine UoM enum mirrors RawMaterial.UnitOfMeasure (per (d)).
        for u in [
            RawMaterial.UnitOfMeasure.EACH,
            RawMaterial.UnitOfMeasure.KG,
            RawMaterial.UnitOfMeasure.M2,
            RawMaterial.UnitOfMeasure.OTHER,
        ]:
            line = self._make(
                raw_material=(
                    self.acme_paint
                    if u == RawMaterial.UnitOfMeasure.OTHER
                    else self.acme_steel
                ),
                unit_of_measure=u,
            )
            line.delete()  # next iteration needs the (bom, raw_material) pair free

    def test_invalid_unit_of_measure_rejected_by_full_clean(self) -> None:
        bad = BOMLine(
            organization=self.acme,
            bom=self.bom,
            raw_material=self.acme_steel,
            quantity=Decimal("1.0000"),
            unit_of_measure="GARBAGE",
            cost_basis_quantity=Decimal("0.2500"),
            cost_reference=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_uom_can_differ_from_raw_material_uom(self) -> None:
        # Key (b) design: BOMLine UoM may be different from the
        # RawMaterial's catalog UoM. Steel is M2 in the catalog; line is KG.
        # The cost_basis_quantity bridges the two for pricing math.
        self.assertEqual(self.acme_steel.unit_of_measure, "M2")
        line = self._make(unit_of_measure=RawMaterial.UnitOfMeasure.KG)
        self.assertNotEqual(line.unit_of_measure, line.raw_material.unit_of_measure)

    # --- Per-BOM uniqueness on raw_material ---------------------------------

    def test_same_material_cannot_appear_twice_in_one_bom(self) -> None:
        self._make(raw_material=self.acme_steel)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(raw_material=self.acme_steel)

    def test_same_material_can_appear_in_different_boms(self) -> None:
        # Two BOMs (e.g. one DRAFT, one SUPERSEDED for same product) can each
        # have their own line for the same material.
        self._make(raw_material=self.acme_steel)
        other_bom = BOM.objects.create(
            organization=self.acme,
            finished_product=self.acme_widget,
            version="v2",
            effective_from=datetime.date(2025, 6, 1),
        )
        line2 = BOMLine.objects.create(
            organization=self.acme,
            bom=other_bom,
            raw_material=self.acme_steel,
            quantity=Decimal("3.0000"),
            unit_of_measure=RawMaterial.UnitOfMeasure.KG,
            cost_basis_quantity=Decimal("0.2500"),
            cost_reference=Decimal("10.00"),
        )
        self.assertIsNotNone(line2.pk)

    # --- CASCADE on bom; PROTECT on raw_material -----------------------------

    def test_deleting_bom_cascades_to_lines(self) -> None:
        line = self._make()
        line_pk = line.pk
        self.bom.delete()
        # Line should be gone — CASCADE.
        self.assertFalse(BOMLine.objects.filter(pk=line_pk).exists())

    def test_raw_material_delete_protected_when_referenced(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme_steel.delete()

    def test_raw_material_delete_protected_even_for_superseded_bom_lines(self) -> None:
        # Spec §15.2: "Old BOM versions remain accessible for audit." That
        # means SUPERSEDED BOMs still pin their raw materials. PROTECT does
        # the right thing without status-aware logic.
        self._make()
        self.bom.status = BOM.Status.SUPERSEDED
        self.bom.save()
        with self.assertRaises(ProtectedError):
            self.acme_steel.delete()

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    # --- Tenancy ------------------------------------------------------------

    def test_for_org_tenancy_isolation(self) -> None:
        self._make()
        # Beta needs its own setup chain.
        beta_steel = RawMaterial.objects.create(
            organization=self.beta,
            sku="STEEL-1",
            name="Beta steel",
            unit_of_measure=RawMaterial.UnitOfMeasure.M2,
            current_cost=Decimal("12.00"),
        )
        beta_bom = BOM.objects.create(
            organization=self.beta,
            finished_product=self.beta_widget,
            version="b1",
            effective_from=datetime.date(2025, 1, 1),
        )
        BOMLine.objects.create(
            organization=self.beta,
            bom=beta_bom,
            raw_material=beta_steel,
            quantity=Decimal("1"),
            unit_of_measure=RawMaterial.UnitOfMeasure.KG,
            cost_basis_quantity=Decimal("1"),
            cost_reference=Decimal("12.00"),
        )
        self.assertEqual(BOMLine.objects.for_org(self.acme).count(), 1)
        self.assertEqual(BOMLine.objects.for_org(self.beta).count(), 1)

    def test_default_ordering_within_bom_is_material_name(self) -> None:
        # ordering = ("bom", "raw_material__name")
        # Within self.bom, lines should sort: Red paint, Steel sheet.
        self._make(raw_material=self.acme_steel)
        BOMLine.objects.create(
            organization=self.acme,
            bom=self.bom,
            raw_material=self.acme_paint,
            quantity=Decimal("1.0000"),
            unit_of_measure=RawMaterial.UnitOfMeasure.L,
            cost_basis_quantity=Decimal("1.0000"),
            cost_reference=Decimal("5.00"),
        )
        names = list(
            BOMLine.objects.for_org(self.acme)
            .filter(bom=self.bom)
            .values_list("raw_material__name", flat=True)
        )
        self.assertEqual(names, ["Red paint", "Steel sheet"])
