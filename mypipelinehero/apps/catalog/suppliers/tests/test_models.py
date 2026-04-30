"""
Tests for Supplier and SupplierProduct models.

Supplier:
  - field defaults (status defaults to ACTIVE)
  - __str__ output
  - per-org uniqueness on name
  - cross-org independence (same name in different orgs)
  - status TextChoices: ACTIVE/INACTIVE/SUSPENDED accepted; invalid rejected
  - PROTECT semantics on FK delete (organization)
  - contact fields default to ""
  - for_org() tenancy isolation
  - default ordering by name

SupplierProduct (the interesting model in this step):
  - The CHECK constraint enforces exactly-one-of-target:
      * both null → IntegrityError
      * both set → IntegrityError
      * product only → OK
      * raw_material only → OK
  - Partial unique indexes:
      * (supplier, product) unique when product not null
      * (supplier, raw_material) unique when raw_material not null
      * Multiple raw-material rows do NOT collide on the (supplier,
        product=NULL) pair (the bug the partial index defends against)
  - PROTECT on supplier, product, raw_material
  - default_cost: zero allowed, negative rejected
  - lead_time_days: NULL allowed; negative rejected at the DB level (the
    PositiveIntegerField CHECK ≥ 0)
  - target property returns the populated side
  - for_org() tenancy isolation

These tests assume Postgres (per project DATABASE_URL). The CHECK and
partial-unique behavior is Postgres-native and would be unreliable on
SQLite even in modern versions.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.materials.models import RawMaterial
from apps.catalog.products.models import Product
from apps.catalog.suppliers.models import Supplier, SupplierProduct
from apps.platform.organizations.models import Organization


class SupplierTestBase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = Organization.objects.create(name="Acme", slug="acme")
        cls.beta = Organization.objects.create(name="Beta", slug="beta")


class SupplierTests(SupplierTestBase):
    def _make(self, **overrides) -> Supplier:
        defaults = dict(organization=self.acme, name="Acme Steel Co")
        defaults.update(overrides)
        return Supplier.objects.create(**defaults)

    def test_creates_with_defaults(self) -> None:
        s = self._make()
        self.assertEqual(s.status, "ACTIVE")
        self.assertEqual(s.contact_name, "")
        self.assertEqual(s.email, "")
        self.assertEqual(s.phone, "")
        self.assertEqual(s.website, "")

    def test_str_returns_name(self) -> None:
        self.assertEqual(str(self._make(name="Foo Co")), "Foo Co")

    def test_status_choices_accepted(self) -> None:
        for status in [
            Supplier.Status.ACTIVE,
            Supplier.Status.INACTIVE,
            Supplier.Status.SUSPENDED,
        ]:
            s = self._make(name=f"S-{status}", status=status)
            self.assertEqual(s.status, status.value)

    def test_invalid_status_rejected_by_full_clean(self) -> None:
        bad = Supplier(
            organization=self.acme,
            name="Bad",
            status="GARBAGE",
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_unique_name_per_org(self) -> None:
        self._make(name="Foo Co")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(name="Foo Co")

    def test_same_name_allowed_in_different_org(self) -> None:
        self._make(name="Foo Co")
        # Should not raise.
        beta_supplier = Supplier.objects.create(organization=self.beta, name="Foo Co")
        self.assertIsNotNone(beta_supplier.pk)

    def test_for_org_tenancy_isolation(self) -> None:
        self._make(name="A1")
        self._make(name="A2")
        Supplier.objects.create(organization=self.beta, name="B1")
        self.assertEqual(
            set(Supplier.objects.for_org(self.acme).values_list("name", flat=True)),
            {"A1", "A2"},
        )
        self.assertEqual(
            list(Supplier.objects.for_org(self.beta).values_list("name", flat=True)),
            ["B1"],
        )

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    def test_default_ordering_is_name(self) -> None:
        self._make(name="Zebra Supply")
        self._make(name="Apple Supply")
        names = list(Supplier.objects.for_org(self.acme).values_list("name", flat=True))
        self.assertEqual(names, ["Apple Supply", "Zebra Supply"])


class SupplierProductTests(SupplierTestBase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.acme_supplier = Supplier.objects.create(
            organization=cls.acme, name="Acme Steel Co"
        )
        cls.beta_supplier = Supplier.objects.create(
            organization=cls.beta, name="Beta Steel Co"
        )
        cls.acme_product = Product.objects.create(
            organization=cls.acme,
            product_type=Product.ProductType.RESALE,
            sku="WIDGET-1",
            name="Widget",
        )
        cls.acme_material = RawMaterial.objects.create(
            organization=cls.acme,
            sku="STEEL-1",
            name="Steel sheet",
            unit_of_measure=RawMaterial.UnitOfMeasure.M2,
            current_cost=Decimal("10.00"),
        )

    def _make_product_offering(self, **overrides) -> SupplierProduct:
        defaults = dict(
            organization=self.acme,
            supplier=self.acme_supplier,
            product=self.acme_product,
            supplier_sku="ACME-W-1",
            default_cost=Decimal("8.00"),
        )
        defaults.update(overrides)
        return SupplierProduct.objects.create(**defaults)

    def _make_material_offering(self, **overrides) -> SupplierProduct:
        defaults = dict(
            organization=self.acme,
            supplier=self.acme_supplier,
            raw_material=self.acme_material,
            supplier_sku="ACME-S-1",
            default_cost=Decimal("9.00"),
        )
        defaults.update(overrides)
        return SupplierProduct.objects.create(**defaults)

    # --- Target XOR (the CHECK constraint) -----------------------------------

    def test_target_xor_allows_product_only(self) -> None:
        sp = self._make_product_offering()
        self.assertEqual(sp.product_id, self.acme_product.pk)
        self.assertIsNone(sp.raw_material_id)

    def test_target_xor_allows_raw_material_only(self) -> None:
        sp = self._make_material_offering()
        self.assertEqual(sp.raw_material_id, self.acme_material.pk)
        self.assertIsNone(sp.product_id)

    def test_target_xor_rejects_both_null(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            SupplierProduct.objects.create(
                organization=self.acme,
                supplier=self.acme_supplier,
                product=None,
                raw_material=None,
                supplier_sku="ORPHAN",
                default_cost=Decimal("1"),
            )

    def test_target_xor_rejects_both_set(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            SupplierProduct.objects.create(
                organization=self.acme,
                supplier=self.acme_supplier,
                product=self.acme_product,
                raw_material=self.acme_material,
                supplier_sku="BOTH",
                default_cost=Decimal("1"),
            )

    # --- Partial unique indexes ---------------------------------------------

    def test_unique_supplier_product_pair(self) -> None:
        self._make_product_offering()
        # Same supplier offering the same product twice — should fail.
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make_product_offering(supplier_sku="DUPE")

    def test_unique_supplier_material_pair(self) -> None:
        self._make_material_offering()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make_material_offering(supplier_sku="DUPE")

    def test_partial_index_does_not_collide_across_target_types(self) -> None:
        """Bug guard: without the partial WHERE clauses on the unique indexes,
        a vanilla UNIQUE on (supplier, product) would treat NULLs as distinct
        and let infinite raw-material rows collide on (supplier, NULL). The
        partial scopes prevent that — both inserts succeed because the
        index applies only when product IS NOT NULL."""
        # Product offering for this supplier.
        self._make_product_offering()
        # Material offering for the same supplier — different target type,
        # should NOT trigger the (supplier, product) uniqueness.
        sp_mat = self._make_material_offering()
        self.assertIsNotNone(sp_mat.pk)

    def test_different_supplier_can_offer_same_product(self) -> None:
        """Same product, two different suppliers — both rows should coexist.
        This is the whole point of SupplierProduct as a join."""
        self._make_product_offering()
        # Need a second supplier in the same org.
        second_supplier = Supplier.objects.create(
            organization=self.acme, name="Second Co"
        )
        sp = SupplierProduct.objects.create(
            organization=self.acme,
            supplier=second_supplier,
            product=self.acme_product,
            supplier_sku="SECOND-W-1",
            default_cost=Decimal("7.50"),
        )
        self.assertIsNotNone(sp.pk)

    # --- Cost / lead time validation ----------------------------------------

    def test_negative_default_cost_rejected_by_validator(self) -> None:
        bad = SupplierProduct(
            organization=self.acme,
            supplier=self.acme_supplier,
            product=self.acme_product,
            supplier_sku="X",
            default_cost=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_zero_default_cost_allowed(self) -> None:
        sp = self._make_product_offering(default_cost=Decimal("0.00"))
        self.assertEqual(sp.default_cost, Decimal("0.00"))

    def test_lead_time_days_can_be_null(self) -> None:
        sp = self._make_product_offering(lead_time_days=None)
        self.assertIsNone(sp.lead_time_days)

    def test_negative_lead_time_rejected_by_db(self) -> None:
        # PositiveIntegerField adds a CHECK lead_time_days >= 0 at the DB level,
        # which is enforced even if Python-side validation is bypassed.
        with self.assertRaises(IntegrityError), transaction.atomic():
            SupplierProduct.objects.create(
                organization=self.acme,
                supplier=self.acme_supplier,
                product=self.acme_product,
                supplier_sku="NEG-LEAD",
                default_cost=Decimal("1"),
                lead_time_days=-5,
            )

    # --- target property -----------------------------------------------------

    def test_target_property_returns_product_when_product_set(self) -> None:
        sp = self._make_product_offering()
        self.assertEqual(sp.target, self.acme_product)

    def test_target_property_returns_raw_material_when_material_set(self) -> None:
        sp = self._make_material_offering()
        self.assertEqual(sp.target, self.acme_material)

    # --- PROTECT semantics ---------------------------------------------------

    def test_supplier_delete_protected_when_referenced(self) -> None:
        self._make_product_offering()
        with self.assertRaises(ProtectedError):
            self.acme_supplier.delete()

    def test_product_delete_protected_when_referenced(self) -> None:
        self._make_product_offering()
        with self.assertRaises(ProtectedError):
            self.acme_product.delete()

    def test_raw_material_delete_protected_when_referenced(self) -> None:
        self._make_material_offering()
        with self.assertRaises(ProtectedError):
            self.acme_material.delete()

    def test_organization_delete_protected(self) -> None:
        self._make_product_offering()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    # --- Tenancy --------------------------------------------------------------

    def test_for_org_tenancy_isolation(self) -> None:
        self._make_product_offering()
        beta_product = Product.objects.create(
            organization=self.beta,
            product_type=Product.ProductType.RESALE,
            sku="B-W-1",
            name="Beta widget",
        )
        SupplierProduct.objects.create(
            organization=self.beta,
            supplier=self.beta_supplier,
            product=beta_product,
            supplier_sku="BETA-W-1",
            default_cost=Decimal("8.00"),
        )
        self.assertEqual(SupplierProduct.objects.for_org(self.acme).count(), 1)
        self.assertEqual(SupplierProduct.objects.for_org(self.beta).count(), 1)

    def test_str_includes_supplier_target_and_cost(self) -> None:
        sp = self._make_product_offering()
        s = str(sp)
        self.assertIn(self.acme_supplier.name, s)
        self.assertIn(self.acme_product.name, s)
        self.assertIn("8.00", s)
