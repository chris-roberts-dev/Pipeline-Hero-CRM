"""
Pricing rule and snapshot models.

Two models in this file:
  - PricingRule: a rule for how to compute a price. Tied to a line type
    (SERVICE/RESALE/MANUFACTURED) and optionally a specific catalog item
    (Service or Product). Stores rule_type-specific parameters as JSON.
  - PricingSnapshot: an immutable record of a computed price for a quote
    line. Written once at pricing time, never updated. When a quote is
    re-priced, a new snapshot is written and the previous one's
    `is_active` flag flips to False (preserving history per §13.3).

Key design decisions (resolved in step 4 design):

1. **Polymorphic target via two nullable FKs + CHECK** — same pattern as
   step 2's SupplierProduct. `target_service` xor `target_product` xor
   neither (= "default rule for this line type"). Coherence CHECK
   enforces SERVICE → target_service / RESALE,MANUFACTURED → target_product.

2. **Single rule_type for v1: MARKUP_PERCENT.** TextChoices means future
   rule types are additive. `parameters` is a JSONField with rule_type-aware
   `clean()` validation.

3. **Higher priority wins.** When multiple rules match a line, the
   resolution algorithm (in 4b) sorts by (target_specificity DESC,
   priority DESC) and takes the first.

4. **No PricingRule uniqueness constraints in v1.** Multiple rules at the
   same specificity level are allowed; priority disambiguates. If field
   experience shows this causes confusion, a uniqueness constraint can be
   added with a follow-up migration.

5. **PricingSnapshot.quote_line_id is BigIntegerField (no FK yet).**
   QuoteLine model doesn't exist yet (later milestone). When it lands,
   converting this column to a real FK is an `AlterField` migration. The
   integer-now/FK-later approach lets the pricing engine and snapshot
   model be fully testable in isolation.

6. **Hybrid concrete + JSON snapshot fields.** Universal money values
   (final price, base cost, markup amount, discount amount) are SQL
   columns for fast aggregate queries. Line-type-specific bits (material
   vs labor split for manufactured, supplier ref for resale) live in the
   `breakdown` JSON. Inputs are captured wholesale in the `inputs` JSON.

7. **Partial unique index on (organization, quote_line_id) WHERE
   is_active = True** — at most one active snapshot per quote line. The
   superseded-snapshots-with-is_active=False history is enabled by the
   partial scope.

8. **engine_version pinned via spec §13.1 row 1149**: included from day
   one as `"1.0"`. Future engine revisions bump this string and old
   snapshots remain unambiguously marked.

Index/constraint name prefix: `pricing_`, all ≤30 chars.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.decimal_precision import (
    MONEY_DECIMAL_PLACES,
    MONEY_MAX_DIGITS,
)
from apps.common.tenancy.models import TenantModel

# The current pricing engine version. Bump this string when the engine's
# math changes in a way that affects snapshot reproducibility. Old
# snapshots retain their captured engine_version for forensic clarity.
PRICING_ENGINE_VERSION = "1.0"


class LineType(models.TextChoices):
    """The three pricing line types per spec §13.1.

    Lifted to module level (not nested on a model) because both PricingRule
    and PricingSnapshot use it. Future Quote/QuoteLine models will reuse
    this enum too, which is part of why it lives outside any single model.
    """

    SERVICE = "SERVICE", "Service"
    RESALE = "RESALE", "Resale Product"
    MANUFACTURED = "MANUFACTURED", "Manufactured Product"


class PricingRule(TenantModel):
    """A rule for how to compute a price.

    Resolution precedence (resolved spec §13.1 line 1144):
      Item-specific rule (target_service or target_product set) overrides
      line-type default (both target FKs null).

    Within the same specificity level, `priority` resolves ties — higher
    priority is applied first.
    """

    class RuleType(models.TextChoices):
        # v1 has one rule type. The TextChoices wrapping is for additive
        # extensibility — adding a SECOND rule_type is a new enum entry,
        # a new branch in clean()'s parameter validation, and a new
        # strategy-engine handler. No schema migration to add an enum value.
        MARKUP_PERCENT = "MARKUP_PERCENT", "Markup percent over cost"

    rule_type = models.CharField(
        max_length=32,
        choices=RuleType.choices,
        help_text=(
            "Which pricing formula this rule represents. Drives how "
            "`parameters` is interpreted."
        ),
    )
    target_line_type = models.CharField(
        max_length=20,
        choices=LineType.choices,
        help_text="Which line type this rule applies to.",
    )

    # Polymorphic target: at most one of target_service / target_product
    # is non-null. Both null = "default rule for this line type, applies
    # to all items."
    target_service = models.ForeignKey(
        "catalog_services.Service",
        on_delete=models.PROTECT,
        related_name="pricing_rules",
        null=True,
        blank=True,
        help_text=(
            "If set, this rule applies only to this specific service. "
            "Mutually exclusive with target_product."
        ),
    )
    target_product = models.ForeignKey(
        "catalog_products.Product",
        on_delete=models.PROTECT,
        related_name="pricing_rules",
        null=True,
        blank=True,
        help_text=(
            "If set, this rule applies only to this specific product. "
            "Mutually exclusive with target_service."
        ),
    )

    parameters = models.JSONField(
        default=dict,
        help_text=(
            "Rule-type-specific parameters. For MARKUP_PERCENT: "
            '{"markup_percent": "0.25"} — Decimal as string. Validated '
            "in clean() against the rule_type."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Soft-disable flag. Inactive rules are skipped by the "
            "resolution algorithm but retained for audit."
        ),
    )
    priority = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Higher number wins when multiple rules match at the same "
            "specificity level. Default 0."
        ),
    )

    class Meta:
        verbose_name = "pricing rule"
        verbose_name_plural = "pricing rules"
        # Most-specific, then highest-priority first. Matches the
        # resolution algorithm: target_service/target_product NULLS LAST,
        # then priority DESC.
        ordering = ("target_line_type", "-priority", "-created_at")
        constraints = [
            # At most one of target_service / target_product is non-null.
            # (Both-null is the legitimate "default rule" case.)
            models.CheckConstraint(
                condition=(
                    models.Q(target_service__isnull=True, target_product__isnull=True)
                    | models.Q(
                        target_service__isnull=False, target_product__isnull=True
                    )
                    | models.Q(
                        target_service__isnull=True, target_product__isnull=False
                    )
                ),
                name="pricing_rule_target_at_most_one",
            ),
            # Coherence: SERVICE line type pairs with target_service (or
            # neither); RESALE/MANUFACTURED pair with target_product (or
            # neither). Cross-pairing is structurally invalid.
            models.CheckConstraint(
                condition=(
                    # SERVICE: target_product must be NULL
                    (
                        models.Q(target_line_type="SERVICE")
                        & models.Q(target_product__isnull=True)
                    )
                    # RESALE/MANUFACTURED: target_service must be NULL
                    | (
                        models.Q(target_line_type__in=["RESALE", "MANUFACTURED"])
                        & models.Q(target_service__isnull=True)
                    )
                ),
                name="pricing_rule_target_coherent",
            ),
        ]
        indexes = [
            # Resolution lookup path: filter by org + line_type + active,
            # then sort by specificity + priority. The is_active=True
            # filter is the hot path so it's leftmost-after-org.
            models.Index(
                fields=("organization", "is_active", "target_line_type"),
                name="pricing_rule_resolution_idx",
            ),
            # Item-specific lookup: "what rule(s) target this service/product?"
            models.Index(
                fields=("organization", "target_service"),
                name="pricing_rule_org_svc_idx",
            ),
            models.Index(
                fields=("organization", "target_product"),
                name="pricing_rule_org_prod_idx",
            ),
        ]

    def __str__(self) -> str:
        target = self.target_service or self.target_product or "(default)"
        return f"{self.get_rule_type_display()} for {self.target_line_type} → {target}"

    def clean(self) -> None:
        """Validate `parameters` against `rule_type`.

        DB-level CHECKs handle the structural integrity (target XOR,
        coherence). This method validates the JSON payload — Postgres
        CHECK constraints can't reach into JSON values cleanly, and the
        validation is per-rule-type which fits Python better than SQL.
        """
        super().clean()
        errors: dict[str, list[str]] = {}

        if self.rule_type == self.RuleType.MARKUP_PERCENT:
            self._clean_markup_percent_parameters(errors)

        if errors:
            raise ValidationError(errors)

    def _clean_markup_percent_parameters(self, errors: dict[str, list[str]]) -> None:
        """MARKUP_PERCENT requires {'markup_percent': <decimal-as-string>}.

        Per spec §13.1: "Negative markup: Allowed at zero; negative
        blocked at PricingRule validation layer." So zero is fine,
        negative is rejected here — not at the strategy engine.
        """
        params = self.parameters or {}

        if not isinstance(params, dict):
            errors.setdefault("parameters", []).append(
                "parameters must be a JSON object."
            )
            return

        if "markup_percent" not in params:
            errors.setdefault("parameters", []).append(
                "MARKUP_PERCENT rule requires a 'markup_percent' parameter."
            )
            return

        raw = params["markup_percent"]
        try:
            value = Decimal(str(raw))
        except (ValueError, TypeError, ArithmeticError):
            errors.setdefault("parameters", []).append(
                f"markup_percent must be a decimal value (got {raw!r})."
            )
            return

        if value < Decimal("0"):
            errors.setdefault("parameters", []).append(
                f"markup_percent must be ≥ 0 (got {value}). "
                "Negative markups are blocked per spec §13.1."
            )


class PricingSnapshot(TenantModel):
    """An immutable record of a computed price for a quote line.

    Per spec §13.3: snapshots are written once at quote time and never
    updated. When re-pricing happens, a new snapshot is written with
    `is_active=True` and the previous snapshot for the same quote_line_id
    is flipped to `is_active=False`. The partial unique index on
    `(organization, quote_line_id) WHERE is_active = True` enforces "at
    most one active snapshot per line" at the database level.

    QuoteLine doesn't exist yet (later milestone) — `quote_line_id` is a
    plain BigIntegerField for now. When QuoteLine lands, a follow-up
    migration converts it to a FK.
    """

    quote_line_id = models.BigIntegerField(
        help_text=(
            "ID of the quote line this snapshot prices. Plain integer "
            "for now; converts to a FK when QuoteLine model lands."
        ),
    )
    line_type = models.CharField(
        max_length=20,
        choices=LineType.choices,
        help_text="Line type at the time of pricing — SERVICE/RESALE/MANUFACTURED.",
    )

    # Universal money breakdown — SQL columns so reporting can aggregate.
    base_cost = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Pre-markup, pre-discount cost basis.",
    )
    markup_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Money added by markup. Zero is allowed; negative is not.",
    )
    discount_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=(
            "Money taken off as discount (before any user override). "
            "Stored as a positive value; subtracted in the math."
        ),
    )
    unit_price_final = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="The unit price actually quoted, after override if any.",
    )

    # Override fields — per §13.1 "shared override and discount layer."
    override_applied = models.BooleanField(
        default=False,
        help_text="True if a user override changed the engine-computed price.",
    )
    override_unit_price = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        null=True,
        blank=True,
        help_text="The override value, if any. NULL when override_applied=False.",
    )
    override_reason = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Required (non-empty) if override_applied=True; ignored otherwise. "
            "Enforced in clean()."
        ),
    )

    # Wholesale captures — JSON for line-type-specific bits.
    inputs = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Full input bundle: catalog item id, supplier_product id "
            "(resale), BOM id (manufactured), labor estimate "
            "(manufactured), applied PricingRule id, etc. Schema is "
            "documented per line type by the strategy engine."
        ),
    )
    breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Line-type-specific cost breakdown beyond the universal "
            "fields above — e.g. material_cost vs labor_cost split for "
            "manufactured products."
        ),
    )

    # Soft-supersede: history is preserved on re-pricing.
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "True for the current snapshot of this quote_line. Flipped "
            "to False when a new snapshot supersedes this one. Never "
            "deleted."
        ),
    )

    # Engine forensics.
    engine_version = models.CharField(
        max_length=16,
        default=PRICING_ENGINE_VERSION,
        help_text=(
            "Pricing engine version that produced this snapshot. Bumped "
            "on engine math changes; old snapshots retain their original "
            "version for reproducibility."
        ),
    )

    class Meta:
        verbose_name = "pricing snapshot"
        verbose_name_plural = "pricing snapshots"
        # Newest first within a quote line is the natural reading order.
        ordering = ("-created_at",)
        constraints = [
            # At most one ACTIVE snapshot per quote line, per organization.
            # Postgres partial unique index — same pattern as M3 step 3's
            # "one ACTIVE BOM per finished_product."
            models.UniqueConstraint(
                fields=("organization", "quote_line_id"),
                condition=models.Q(is_active=True),
                name="pricing_snap_uniq_active_qline",
            ),
            # Override coherence: if override_applied is True, override_unit_price
            # must be set; if False, it must be NULL. The override_reason text
            # check (non-empty when override_applied) is a `clean()` concern
            # because Postgres CHECK on text emptiness is awkward.
            models.CheckConstraint(
                condition=(
                    models.Q(override_applied=False, override_unit_price__isnull=True)
                    | models.Q(override_applied=True, override_unit_price__isnull=False)
                ),
                name="pricing_snap_override_coherent",
            ),
        ]
        indexes = [
            # Lookup by quote line — the most common path.
            models.Index(
                fields=("organization", "quote_line_id", "-created_at"),
                name="pricing_snap_org_qline_idx",
            ),
            # Reporting aggregations by line type.
            models.Index(
                fields=("organization", "line_type", "is_active"),
                name="pricing_snap_org_type_act_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Snapshot ql={self.quote_line_id} {self.line_type} "
            f"@ {self.unit_price_final}"
        )

    def clean(self) -> None:
        """Override-reason consistency: required when override_applied."""
        super().clean()
        errors: dict[str, list[str]] = {}

        if self.override_applied and not (self.override_reason or "").strip():
            errors.setdefault("override_reason", []).append(
                "override_reason is required when override_applied is True."
            )

        if errors:
            raise ValidationError(errors)
