"""
Tests for Product model.

Covers:
  - field defaults (is_active, description)
  - __str__ output (sku and name)
  - product_type choices accepted; invalid type rejected by full_clean
  - per-org uniqueness on sku
  - cross-org independence (same sku allowed in different orgs)
  - PROTECT semantics on FK delete (organization)
  - Meta.ordering
  - for_org() tenancy isolation, including chaining with .filter()
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.products.models import Product
from apps.platform.organizations.models import Organization


class ProductTestBase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = Organization.objects.create(name="Acme", slug="acme")
        cls.beta = Organization.objects.create(name="Beta", slug="beta")


class ProductTests(ProductTestBase):
    def _make(self, **overrides) -> Product:
        defaults = dict(
            organization=self.acme,
            product_type=Product.ProductType.RESALE,
            sku="WIDGET-100",
            name="Widget",
        )
        defaults.update(overrides)
        return Product.objects.create(**defaults)

    def test_creates_with_defaults(self) -> None:
        p = self._make()
        self.assertTrue(p.is_active)
        self.assertEqual(p.description, "")

    def test_str_includes_sku_and_name(self) -> None:
        p = self._make(sku="ABC", name="Widget")
        self.assertIn("ABC", str(p))
        self.assertIn("Widget", str(p))

    def test_product_type_choices_accepted(self) -> None:
        # Both valid types accepted.
        r = self._make(sku="R-1", product_type=Product.ProductType.RESALE)
        m = self._make(sku="M-1", product_type=Product.ProductType.MANUFACTURED)
        self.assertEqual(r.product_type, "RESALE")
        self.assertEqual(m.product_type, "MANUFACTURED")

    def test_invalid_product_type_rejected_by_full_clean(self) -> None:
        bad = Product(
            organization=self.acme,
            product_type="GARBAGE",
            sku="BAD",
            name="Bad",
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_unique_sku_per_org(self) -> None:
        self._make(sku="WIDGET-100")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(sku="WIDGET-100")

    def test_same_sku_allowed_in_different_org(self) -> None:
        self._make(sku="WIDGET-100")
        # Should not raise.
        beta_widget = Product.objects.create(
            organization=self.beta,
            product_type=Product.ProductType.RESALE,
            sku="WIDGET-100",
            name="Beta widget",
        )
        self.assertIsNotNone(beta_widget.pk)

    def test_for_org_tenancy_isolation(self) -> None:
        self._make(sku="A1")
        self._make(sku="A2")
        Product.objects.create(
            organization=self.beta,
            product_type=Product.ProductType.RESALE,
            sku="B1",
            name="B1",
        )
        self.assertEqual(
            set(Product.objects.for_org(self.acme).values_list("sku", flat=True)),
            {"A1", "A2"},
        )
        self.assertEqual(
            list(Product.objects.for_org(self.beta).values_list("sku", flat=True)),
            ["B1"],
        )

    def test_for_org_filter_by_type(self) -> None:
        self._make(sku="R-1", product_type=Product.ProductType.RESALE)
        self._make(sku="M-1", product_type=Product.ProductType.MANUFACTURED)
        resale = list(
            Product.objects.for_org(self.acme)
            .filter(product_type=Product.ProductType.RESALE)
            .values_list("sku", flat=True)
        )
        self.assertEqual(resale, ["R-1"])

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    def test_default_ordering_is_name(self) -> None:
        Product.objects.create(
            organization=self.acme,
            product_type=Product.ProductType.RESALE,
            sku="Z",
            name="Zebra product",
        )
        Product.objects.create(
            organization=self.acme,
            product_type=Product.ProductType.RESALE,
            sku="A",
            name="Apple product",
        )
        names = list(Product.objects.for_org(self.acme).values_list("name", flat=True))
        self.assertEqual(names, ["Apple product", "Zebra product"])
