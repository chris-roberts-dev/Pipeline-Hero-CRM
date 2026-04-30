"""
Tests for PricingRule and PricingSnapshot models.

PricingRule:
  - field defaults (is_active, priority, parameters)
  - rule_type and target_line_type TextChoices
  - **Target XOR CHECK**: at most one of target_service / target_product
    is non-null. Three valid states: both-null (default rule), service
    only, product only. One invalid: both set.
  - **Coherence CHECK**: target_line_type = SERVICE pairs only with
    target_service; RESALE/MANUFACTURED pair only with target_product.
    Cross-pairing rejected at DB level.
  - clean(): MARKUP_PERCENT requires {'markup_percent': decimal-string};
    negative markup_percent rejected (per spec §13.1)
  - PROTECT on organization, target_service, target_product
  - for_org() tenancy isolation

PricingSnapshot:
  - field defaults (is_active=True, engine_version="1.0", override_applied=False)
  - **Active uniqueness**: at most one is_active=True snapshot per
    (organization, quote_line_id). Multiple inactive snapshots allowed
    (re-pricing history per §13.3).
  - **Override coherence CHECK**: override_applied + override_unit_price
    agree at the DB level.
  - clean(): override_applied=True requires non-empty override_reason.
  - All money validators (zero allowed, negative rejected)
  - quote_line_id is BigIntegerField (not FK) — accepts arbitrary values
  - PROTECT on organization
  - for_org() tenancy isolation

Tests run against Postgres — partial unique indexes and the CHECK
constraints are Postgres-native.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.catalog.pricing.models import (
    LineType,
    PricingRule,
    PricingSnapshot,
)
from apps.catalog.products.models import Product
from apps.catalog.services.models import Service, ServiceCategory
from apps.platform.organizations.models import Organization


class PricingTestBase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.acme = Organization.objects.create(name="Acme", slug="acme")
        cls.beta = Organization.objects.create(name="Beta", slug="beta")
        cls.acme_cat = ServiceCategory.objects.create(
            organization=cls.acme, code="PLUMB", name="Plumbing"
        )
        cls.acme_service = Service.objects.create(
            organization=cls.acme,
            category=cls.acme_cat,
            code="DRAIN",
            name="Drain cleaning",
            catalog_price=Decimal("199.00"),
        )
        cls.acme_product = Product.objects.create(
            organization=cls.acme,
            product_type=Product.ProductType.RESALE,
            sku="WIDGET-1",
            name="Widget",
        )


# ---------------------------------------------------------------------------
# PricingRule
# ---------------------------------------------------------------------------


class PricingRuleTests(PricingTestBase):
    def _make(self, **overrides) -> PricingRule:
        defaults = dict(
            organization=self.acme,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type=LineType.SERVICE,
            parameters={"markup_percent": "0.25"},
        )
        defaults.update(overrides)
        return PricingRule.objects.create(**defaults)

    def test_creates_with_defaults(self) -> None:
        r = self._make()
        self.assertTrue(r.is_active)
        self.assertEqual(r.priority, 0)
        self.assertEqual(r.parameters, {"markup_percent": "0.25"})
        self.assertIsNone(r.target_service_id)
        self.assertIsNone(r.target_product_id)

    def test_str_includes_rule_type_line_type_target(self) -> None:
        r = self._make(target_service=self.acme_service)
        s = str(r)
        self.assertIn("Markup", s)
        self.assertIn("SERVICE", s)
        self.assertIn(self.acme_service.name, s)

    def test_str_default_rule_marks_target_as_default(self) -> None:
        r = self._make()
        self.assertIn("default", str(r))

    # --- Target XOR CHECK ---------------------------------------------------

    def test_target_at_most_one_allows_neither_set(self) -> None:
        # Default rule for the line type — no specific target.
        r = self._make()
        self.assertIsNone(r.target_service_id)
        self.assertIsNone(r.target_product_id)

    def test_target_at_most_one_allows_service_only(self) -> None:
        r = self._make(target_service=self.acme_service)
        self.assertEqual(r.target_service_id, self.acme_service.pk)
        self.assertIsNone(r.target_product_id)

    def test_target_at_most_one_allows_product_only(self) -> None:
        r = self._make(
            target_line_type=LineType.RESALE,
            target_product=self.acme_product,
        )
        self.assertEqual(r.target_product_id, self.acme_product.pk)
        self.assertIsNone(r.target_service_id)

    def test_target_at_most_one_rejects_both_set(self) -> None:
        # NOTE: this case is *also* blocked by the coherence CHECK because
        # SERVICE + target_product is incoherent. We exercise the explicit
        # both-set path here; the coherence-only test below covers the
        # cross-pairing failure mode separately.
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(
                target_line_type=LineType.SERVICE,
                target_service=self.acme_service,
                target_product=self.acme_product,
            )

    # --- Coherence CHECK ----------------------------------------------------

    def test_coherence_service_line_type_rejects_target_product(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(
                target_line_type=LineType.SERVICE,
                target_product=self.acme_product,
                # target_service intentionally not set — this isolates
                # the coherence failure (line_type SERVICE, target_product set)
                # from the at-most-one failure.
            )

    def test_coherence_resale_line_type_rejects_target_service(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(
                target_line_type=LineType.RESALE,
                target_service=self.acme_service,
            )

    def test_coherence_manufactured_line_type_rejects_target_service(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(
                target_line_type=LineType.MANUFACTURED,
                target_service=self.acme_service,
            )

    def test_coherence_default_rule_works_for_all_line_types(self) -> None:
        # Both targets null is valid for any line type.
        for lt in [LineType.SERVICE, LineType.RESALE, LineType.MANUFACTURED]:
            r = self._make(target_line_type=lt)
            self.assertIsNotNone(r.pk)

    # --- clean() / parameter validation -------------------------------------

    def test_markup_percent_requires_parameter(self) -> None:
        bad = PricingRule(
            organization=self.acme,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type=LineType.SERVICE,
            parameters={},  # missing markup_percent
        )
        with self.assertRaises(ValidationError) as ctx:
            bad.full_clean()
        self.assertIn("parameters", ctx.exception.message_dict)

    def test_markup_percent_zero_allowed(self) -> None:
        r = PricingRule(
            organization=self.acme,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type=LineType.SERVICE,
            parameters={"markup_percent": "0"},
        )
        # Should not raise — zero markup is allowed per spec §13.1.
        r.full_clean()

    def test_markup_percent_negative_rejected(self) -> None:
        bad = PricingRule(
            organization=self.acme,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type=LineType.SERVICE,
            parameters={"markup_percent": "-0.10"},
        )
        with self.assertRaises(ValidationError) as ctx:
            bad.full_clean()
        # Spec §13.1: "Negative markup blocked at PricingRule validation"
        msg = str(ctx.exception.message_dict.get("parameters", []))
        self.assertIn("0", msg)

    def test_markup_percent_non_numeric_rejected(self) -> None:
        bad = PricingRule(
            organization=self.acme,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type=LineType.SERVICE,
            parameters={"markup_percent": "not a number"},
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_parameters_must_be_dict(self) -> None:
        bad = PricingRule(
            organization=self.acme,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type=LineType.SERVICE,
            parameters=["not", "a", "dict"],
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_invalid_rule_type_rejected_by_full_clean(self) -> None:
        bad = PricingRule(
            organization=self.acme,
            rule_type="GARBAGE",
            target_line_type=LineType.SERVICE,
            parameters={"markup_percent": "0.25"},
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_invalid_target_line_type_rejected_by_full_clean(self) -> None:
        bad = PricingRule(
            organization=self.acme,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type="GARBAGE",
            parameters={"markup_percent": "0.25"},
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    # --- PROTECT semantics --------------------------------------------------

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    def test_target_service_delete_protected_when_referenced(self) -> None:
        self._make(target_service=self.acme_service)
        with self.assertRaises(ProtectedError):
            self.acme_service.delete()

    def test_target_product_delete_protected_when_referenced(self) -> None:
        self._make(
            target_line_type=LineType.RESALE,
            target_product=self.acme_product,
        )
        with self.assertRaises(ProtectedError):
            self.acme_product.delete()

    # --- Tenancy ------------------------------------------------------------

    def test_for_org_tenancy_isolation(self) -> None:
        self._make()
        beta_cat = ServiceCategory.objects.create(
            organization=self.beta, code="X", name="X"
        )
        beta_service = Service.objects.create(
            organization=self.beta,
            category=beta_cat,
            code="X",
            name="X",
            catalog_price=Decimal("1"),
        )
        PricingRule.objects.create(
            organization=self.beta,
            rule_type=PricingRule.RuleType.MARKUP_PERCENT,
            target_line_type=LineType.SERVICE,
            target_service=beta_service,
            parameters={"markup_percent": "0.10"},
        )
        self.assertEqual(PricingRule.objects.for_org(self.acme).count(), 1)
        self.assertEqual(PricingRule.objects.for_org(self.beta).count(), 1)

    def test_priority_can_be_zero_or_positive(self) -> None:
        # PositiveIntegerField allows 0; this is just documenting our default
        # and that arbitrary positive values work.
        r0 = self._make(priority=0)
        r100 = self._make(target_line_type=LineType.RESALE, priority=100)
        self.assertEqual(r0.priority, 0)
        self.assertEqual(r100.priority, 100)


# ---------------------------------------------------------------------------
# PricingSnapshot
# ---------------------------------------------------------------------------


class PricingSnapshotTests(PricingTestBase):
    def _make(self, **overrides) -> PricingSnapshot:
        defaults = dict(
            organization=self.acme,
            quote_line_id=1001,
            line_type=LineType.SERVICE,
            base_cost=Decimal("100.00"),
            markup_amount=Decimal("25.00"),
            discount_amount=Decimal("0.00"),
            unit_price_final=Decimal("125.00"),
            inputs={"service_id": 42, "rule_id": 7},
            breakdown={},
        )
        defaults.update(overrides)
        return PricingSnapshot.objects.create(**defaults)

    def test_creates_with_defaults(self) -> None:
        s = self._make()
        self.assertTrue(s.is_active)
        self.assertEqual(s.engine_version, "1.0")
        self.assertFalse(s.override_applied)
        self.assertIsNone(s.override_unit_price)
        self.assertEqual(s.override_reason, "")
        self.assertIsNotNone(s.created_at)

    def test_str_includes_quote_line_type_and_price(self) -> None:
        s = self._make(quote_line_id=42)
        result = str(s)
        self.assertIn("42", result)
        self.assertIn("SERVICE", result)
        self.assertIn("125.00", result)

    # --- Active uniqueness via partial index --------------------------------

    def test_only_one_active_snapshot_per_quote_line(self) -> None:
        self._make(quote_line_id=500, is_active=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(quote_line_id=500, is_active=True)

    def test_inactive_snapshots_can_accumulate_for_same_quote_line(self) -> None:
        # The re-pricing history pattern: many is_active=False snapshots
        # plus one is_active=True for the same quote_line.
        self._make(quote_line_id=500, is_active=False)
        self._make(quote_line_id=500, is_active=False)
        self._make(quote_line_id=500, is_active=False)
        # Plus one active.
        self._make(quote_line_id=500, is_active=True)
        snaps = PricingSnapshot.objects.for_org(self.acme).filter(quote_line_id=500)
        self.assertEqual(snaps.count(), 4)
        self.assertEqual(snaps.filter(is_active=True).count(), 1)

    def test_active_uniqueness_is_per_quote_line(self) -> None:
        # Different quote lines can each have their own active snapshot.
        self._make(quote_line_id=500, is_active=True)
        s2 = self._make(quote_line_id=501, is_active=True)
        self.assertIsNotNone(s2.pk)

    def test_active_uniqueness_is_per_organization(self) -> None:
        # quote_line_id 500 in acme and quote_line_id 500 in beta — both
        # can be active because the partial unique scopes by organization.
        self._make(quote_line_id=500, is_active=True)
        beta_snap = PricingSnapshot.objects.create(
            organization=self.beta,
            quote_line_id=500,
            line_type=LineType.SERVICE,
            base_cost=Decimal("100.00"),
            markup_amount=Decimal("25.00"),
            discount_amount=Decimal("0.00"),
            unit_price_final=Decimal("125.00"),
        )
        self.assertIsNotNone(beta_snap.pk)

    # --- Override coherence CHECK -------------------------------------------

    def test_override_coherent_no_override_no_price(self) -> None:
        # Default state: override_applied=False, override_unit_price=NULL.
        s = self._make()
        self.assertFalse(s.override_applied)
        self.assertIsNone(s.override_unit_price)

    def test_override_coherent_with_override_with_price(self) -> None:
        s = self._make(
            override_applied=True,
            override_unit_price=Decimal("99.00"),
            override_reason="Customer negotiated discount",
        )
        self.assertTrue(s.override_applied)
        self.assertEqual(s.override_unit_price, Decimal("99.00"))

    def test_override_coherent_rejects_applied_without_price(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(
                override_applied=True,
                override_unit_price=None,
                override_reason="oops forgot price",
            )

    def test_override_coherent_rejects_price_without_applied(self) -> None:
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._make(
                override_applied=False,
                override_unit_price=Decimal("99.00"),
            )

    # --- override_reason clean() validation ---------------------------------

    def test_override_reason_required_when_applied(self) -> None:
        bad = PricingSnapshot(
            organization=self.acme,
            quote_line_id=1,
            line_type=LineType.SERVICE,
            base_cost=Decimal("100"),
            markup_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            unit_price_final=Decimal("100"),
            override_applied=True,
            override_unit_price=Decimal("99"),
            override_reason="",  # empty
        )
        with self.assertRaises(ValidationError) as ctx:
            bad.full_clean()
        self.assertIn("override_reason", ctx.exception.message_dict)

    def test_override_reason_required_rejects_whitespace_only(self) -> None:
        bad = PricingSnapshot(
            organization=self.acme,
            quote_line_id=1,
            line_type=LineType.SERVICE,
            base_cost=Decimal("100"),
            markup_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            unit_price_final=Decimal("100"),
            override_applied=True,
            override_unit_price=Decimal("99"),
            override_reason="   ",  # whitespace
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_override_reason_optional_when_not_applied(self) -> None:
        s = self._make()  # override_applied=False (default), reason=""
        s.full_clean()  # should not raise

    # --- Money validators ---------------------------------------------------

    def test_negative_base_cost_rejected_by_validator(self) -> None:
        bad = PricingSnapshot(
            organization=self.acme,
            quote_line_id=1,
            line_type=LineType.SERVICE,
            base_cost=Decimal("-1"),
            markup_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            unit_price_final=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_negative_markup_amount_rejected_by_validator(self) -> None:
        bad = PricingSnapshot(
            organization=self.acme,
            quote_line_id=1,
            line_type=LineType.SERVICE,
            base_cost=Decimal("100"),
            markup_amount=Decimal("-5"),
            discount_amount=Decimal("0"),
            unit_price_final=Decimal("95"),
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()

    def test_zero_money_values_allowed(self) -> None:
        # Edge case: a free service (e.g. zero-cost demo line).
        s = self._make(
            base_cost=Decimal("0"),
            markup_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            unit_price_final=Decimal("0"),
        )
        s.full_clean()
        self.assertEqual(s.unit_price_final, Decimal("0"))

    # --- quote_line_id is BigIntegerField (no FK) ---------------------------

    def test_quote_line_id_accepts_arbitrary_integer(self) -> None:
        # No FK, no constraint — just an integer column. This proves the
        # snapshot can be written before the QuoteLine model exists.
        for qline_id in [1, 999999, 2**40]:
            s = self._make(quote_line_id=qline_id, is_active=False)
            self.assertEqual(s.quote_line_id, qline_id)

    # --- Engine version pinning ---------------------------------------------

    def test_engine_version_defaults_to_1_0(self) -> None:
        s = self._make()
        self.assertEqual(s.engine_version, "1.0")

    def test_engine_version_can_be_explicitly_set(self) -> None:
        # Future engine bump scenario.
        s = self._make(engine_version="2.0")
        self.assertEqual(s.engine_version, "2.0")

    # --- JSON fields --------------------------------------------------------

    def test_inputs_and_breakdown_default_to_empty_dict(self) -> None:
        # Created via direct constructor (not _make) to test bare defaults.
        s = PricingSnapshot.objects.create(
            organization=self.acme,
            quote_line_id=1,
            line_type=LineType.SERVICE,
            base_cost=Decimal("100"),
            markup_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            unit_price_final=Decimal("100"),
        )
        self.assertEqual(s.inputs, {})
        self.assertEqual(s.breakdown, {})

    def test_breakdown_stores_arbitrary_json(self) -> None:
        # Manufactured-product breakdown shape per §13.3: material + labor split.
        s = self._make(
            line_type=LineType.MANUFACTURED,
            breakdown={
                "material_cost": "75.00",
                "labor_cost": "25.00",
                "labor_hours": "0.5",
            },
        )
        self.assertEqual(s.breakdown["material_cost"], "75.00")
        self.assertEqual(s.breakdown["labor_hours"], "0.5")

    # --- PROTECT semantics --------------------------------------------------

    def test_organization_delete_protected(self) -> None:
        self._make()
        with self.assertRaises(ProtectedError):
            self.acme.delete()

    # --- Tenancy ------------------------------------------------------------

    def test_for_org_tenancy_isolation(self) -> None:
        self._make(quote_line_id=1)
        PricingSnapshot.objects.create(
            organization=self.beta,
            quote_line_id=1,
            line_type=LineType.SERVICE,
            base_cost=Decimal("100"),
            markup_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            unit_price_final=Decimal("100"),
        )
        self.assertEqual(PricingSnapshot.objects.for_org(self.acme).count(), 1)
        self.assertEqual(PricingSnapshot.objects.for_org(self.beta).count(), 1)

    def test_default_ordering_newest_first(self) -> None:
        # ordering = ("-created_at",)
        s1 = self._make(quote_line_id=1, is_active=False)
        s2 = self._make(quote_line_id=2, is_active=False)
        s3 = self._make(quote_line_id=3, is_active=False)
        ids = list(
            PricingSnapshot.objects.for_org(self.acme).values_list("id", flat=True)
        )
        # Newest first → s3, s2, s1 (auto-increment IDs ascend with time).
        self.assertEqual(ids, [s3.id, s2.id, s1.id])
