"""
System capability registry.

Single source of truth for every capability code the platform ships. The
data migration that seeds `Capability` rows reads from this module; the
permission evaluator may reference these constants by symbolic name; and
the default-role seeding in the next step uses these sets to build each
role's capability assignment.

Structure:
  CAPABILITIES — the flat list of CapabilitySpec records. Codes here must
                 match the exact strings in spec §10.3.
  by_domain()  — grouped view, used when rendering the admin or org-admin
                 role-editing UI.

Rules for edits:
  - ADDING a capability: append a new CapabilitySpec and write a new data
    migration that adds the row. Never mutate existing codes in place.
  - REMOVING a capability is a breaking change — never do it in a point
    release without a deprecation window and a migration that rewrites
    affected RoleCapability / MembershipCapabilityGrant rows.
  - RENAMING a code is forbidden. Role assignments and audit events
    reference codes; renames break history.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySpec:
    """A capability's canonical definition.

    Frozen so accidental mutation of the registry can't happen at import
    time. The `domain` is derived from the code's prefix for UI grouping.
    """

    code: str
    name: str
    domain: str
    description: str = ""


# ---------------------------------------------------------------------------
# Capability registry
# ---------------------------------------------------------------------------
# Codes and names are copied verbatim from spec §10.3. Where the spec has a
# notes column, the notes are captured in `description` for display in the
# admin / role-editing UI. Notes that describe implementation behavior (e.g.
# "audit event required") are NOT copied here — those are evaluator/service
# concerns, not user-facing descriptions.

CAPABILITIES: list[CapabilitySpec] = [
    # --- Lead Management -------------------------------------------------
    CapabilitySpec(
        "leads.view",
        "View leads",
        "leads",
        "Required for all lead list and detail access.",
    ),
    CapabilitySpec("leads.create", "Create leads", "leads"),
    CapabilitySpec(
        "leads.edit",
        "Edit leads",
        "leads",
        "Edit leads you own. Object-level ownership check applies.",
    ),
    CapabilitySpec(
        "leads.edit_any",
        "Edit any lead",
        "leads",
        "Overrides the default ownership restriction.",
    ),
    CapabilitySpec("leads.archive", "Archive leads", "leads"),
    CapabilitySpec(
        "leads.convert",
        "Convert lead to quote",
        "leads",
        "Requires the 'Create quotes' capability as well.",
    ),
    CapabilitySpec("leads.assign", "Assign lead ownership", "leads"),
    # --- Quote Management ------------------------------------------------
    CapabilitySpec("quotes.view", "View quotes", "quotes"),
    CapabilitySpec("quotes.create", "Create quotes / new versions", "quotes"),
    CapabilitySpec(
        "quotes.edit",
        "Edit draft quotes",
        "quotes",
        "Applies only to DRAFT status quote versions.",
    ),
    CapabilitySpec(
        "quotes.send",
        "Send quote to client",
        "quotes",
        "Applies only to DRAFT status quote versions.",
    ),
    CapabilitySpec(
        "quotes.retract",
        "Retract a sent quote",
        "quotes",
        "The sent version remains immutable; a successor draft is created.",
    ),
    CapabilitySpec(
        "quotes.approve",
        "Accept / approve a quote",
        "quotes",
        "Internal acceptance. Highest-trust quote action.",
    ),
    CapabilitySpec("quotes.decline", "Mark quote declined", "quotes"),
    CapabilitySpec("quotes.line.override_price", "Override line item price", "quotes"),
    CapabilitySpec(
        "quotes.line.apply_discount", "Apply discount to line or quote", "quotes"
    ),
    CapabilitySpec(
        "quotes.delete_draft",
        "Delete a draft quote version",
        "quotes",
        "Hard delete. Only DRAFT versions may be deleted.",
    ),
    # --- Client Management -----------------------------------------------
    CapabilitySpec("clients.view", "View client records", "clients"),
    CapabilitySpec(
        "clients.create",
        "Create new clients",
        "clients",
        "Also triggered by the quote acceptance flow.",
    ),
    CapabilitySpec("clients.edit", "Edit client details", "clients"),
    CapabilitySpec(
        "clients.merge",
        "Merge duplicate client records",
        "clients",
        "High-risk operation. Typically restricted to managers.",
    ),
    CapabilitySpec("clients.deactivate", "Deactivate a client", "clients"),
    CapabilitySpec("clients.contacts.manage", "Manage client contacts", "clients"),
    CapabilitySpec("clients.locations.manage", "Manage client locations", "clients"),
    # --- Sales Order Management ------------------------------------------
    CapabilitySpec("orders.view", "View sales orders", "orders"),
    CapabilitySpec(
        "orders.edit",
        "Edit order notes / metadata",
        "orders",
        "Commercial lines are immutable after acceptance.",
    ),
    CapabilitySpec(
        "orders.cancel",
        "Cancel an order",
        "orders",
        "Only permitted when no active fulfillment artifacts exist. Reason required.",
    ),
    CapabilitySpec(
        "orders.generate_fulfillment",
        "Manually trigger fulfillment generation",
        "orders",
        "Fulfillment artifact generation is normally system-triggered.",
    ),
    # --- Catalog Management ----------------------------------------------
    CapabilitySpec(
        "catalog.view",
        "View catalog items",
        "catalog",
        "Required for quote line item selection.",
    ),
    CapabilitySpec("catalog.services.manage", "Manage services", "catalog"),
    CapabilitySpec("catalog.products.manage", "Manage products", "catalog"),
    CapabilitySpec("catalog.materials.manage", "Manage raw materials", "catalog"),
    CapabilitySpec("catalog.suppliers.manage", "Manage suppliers", "catalog"),
    CapabilitySpec("catalog.bom.manage", "Manage BOMs", "catalog"),
    CapabilitySpec("catalog.pricing_rules.manage", "Manage pricing rules", "catalog"),
    CapabilitySpec(
        "catalog.pricing_rules.view",
        "View pricing rules",
        "catalog",
        "Required for quote pricing transparency.",
    ),
    # --- Work Order Management -------------------------------------------
    CapabilitySpec("workorders.view", "View work orders", "workorders"),
    CapabilitySpec("workorders.assign", "Assign / unassign work orders", "workorders"),
    CapabilitySpec(
        "workorders.update_status",
        "Update work order status",
        "workorders",
        "Must be the assignee unless 'Full work order management' is held.",
    ),
    CapabilitySpec(
        "workorders.manage",
        "Full work order management",
        "workorders",
        "Includes cancel, reassign, and override.",
    ),
    CapabilitySpec(
        "workorders.complete",
        "Complete work order",
        "workorders",
        "Outcome notes are required to complete.",
    ),
    CapabilitySpec(
        "workorders.view_all",
        "View work orders across all assignees",
        "workorders",
        "Without this, users see only their own work orders.",
    ),
    # --- Purchase Order Management ---------------------------------------
    CapabilitySpec("purchasing.view", "View purchase orders", "purchasing"),
    CapabilitySpec("purchasing.create", "Create POs from order lines", "purchasing"),
    CapabilitySpec(
        "purchasing.edit",
        "Edit draft POs",
        "purchasing",
        "Applies only to DRAFT status POs.",
    ),
    CapabilitySpec("purchasing.submit", "Submit PO to supplier", "purchasing"),
    CapabilitySpec(
        "purchasing.receive", "Record receipt against PO lines", "purchasing"
    ),
    CapabilitySpec(
        "purchasing.cancel",
        "Cancel a PO",
        "purchasing",
        "Only before supplier processing.",
    ),
    # --- Build Order Management ------------------------------------------
    CapabilitySpec("build.view", "View build orders", "build"),
    CapabilitySpec(
        "build.manage", "Manage build orders", "build", "Start, hold, resume, cancel."
    ),
    CapabilitySpec("build.labor.record", "Record labor entries", "build"),
    CapabilitySpec(
        "build.labor.edit_any",
        "Edit any user's labor entries",
        "build",
        "Managers only.",
    ),
    CapabilitySpec(
        "build.qa.review",
        "QA review of builds",
        "build",
        "Approve or reject builds in quality review.",
    ),
    CapabilitySpec(
        "build.cost.view",
        "View build cost analysis",
        "build",
        "View estimated vs actual cost. May be restricted by sensitivity.",
    ),
    # --- Invoicing and Billing -------------------------------------------
    CapabilitySpec("billing.view", "View invoices and payments", "billing"),
    CapabilitySpec("billing.invoice.create", "Create invoices from orders", "billing"),
    CapabilitySpec("billing.invoice.send", "Send invoice to client", "billing"),
    CapabilitySpec(
        "billing.invoice.void",
        "Void an invoice",
        "billing",
        "Cannot void a PAID invoice.",
    ),
    CapabilitySpec(
        "billing.payment.record", "Record payment against invoice", "billing"
    ),
    CapabilitySpec(
        "billing.payment.edit",
        "Record payment correction or adjustment",
        "billing",
        "Posted payment history is never mutated in place; this creates a reversal or adjustment.",
    ),
    CapabilitySpec(
        "billing.reports.view",
        "View billing reports",
        "billing",
        "Balance summaries and billing overviews.",
    ),
    # --- Task Management -------------------------------------------------
    CapabilitySpec("tasks.view", "View tasks", "tasks"),
    CapabilitySpec("tasks.create", "Create tasks", "tasks"),
    CapabilitySpec(
        "tasks.edit",
        "Edit tasks",
        "tasks",
        "Must be creator, assignee, or have 'Full task management'.",
    ),
    CapabilitySpec("tasks.assign", "Assign or reassign tasks", "tasks"),
    CapabilitySpec("tasks.complete", "Mark task completed", "tasks"),
    CapabilitySpec(
        "tasks.manage",
        "Full task management",
        "tasks",
        "Includes cancel, reopen, and override. Reopen requires a reason.",
    ),
    # --- Communications --------------------------------------------------
    CapabilitySpec(
        "communications.view", "View communication history", "communications"
    ),
    CapabilitySpec(
        "communications.log", "Log inbound or outbound communication", "communications"
    ),
    CapabilitySpec(
        "communications.send",
        "Send supported outbound communication",
        "communications",
        "Delivery may be asynchronous.",
    ),
    CapabilitySpec(
        "communications.manage",
        "Edit communication metadata",
        "communications",
        "Original message body is immutable once sent.",
    ),
    # --- Reporting -------------------------------------------------------
    CapabilitySpec("reporting.view", "Access standard reports", "reporting"),
    CapabilitySpec("reporting.export", "Export report data", "reporting"),
    CapabilitySpec(
        "reporting.advanced",
        "Access cost and margin reports",
        "reporting",
        "Sensitive; restricted.",
    ),
    # --- Tenant Administration -------------------------------------------
    CapabilitySpec("admin.members.view", "View org members and roles", "admin"),
    CapabilitySpec("admin.members.invite", "Invite new members", "admin"),
    CapabilitySpec("admin.members.deactivate", "Deactivate a membership", "admin"),
    CapabilitySpec("admin.members.suspend", "Suspend a membership", "admin"),
    CapabilitySpec("admin.roles.view", "View role definitions", "admin"),
    CapabilitySpec("admin.roles.manage", "Create / edit org-defined roles", "admin"),
    CapabilitySpec("admin.roles.assign", "Assign roles to members", "admin"),
    CapabilitySpec(
        "admin.capabilities.grant", "Grant per-membership capability overrides", "admin"
    ),
    CapabilitySpec(
        "admin.org.settings", "Edit org settings", "admin", "Name, logo, timezone, etc."
    ),
    CapabilitySpec(
        "admin.numbering.configure", "Configure entity numbering prefixes", "admin"
    ),
    # --- Platform Support (cross-tenant) ---------------------------------
    # These capabilities are NOT held by any seeded default role today.
    # Spec §7.4: support users are global and access tenants under
    # controlled conditions. In v1 only superusers have access (via
    # evaluator step 1 short-circuit). A future platform-staff role will
    # hold these explicitly without needing superuser privilege.
    CapabilitySpec(
        "support.impersonation.start",
        "Start a tenant impersonation session",
        "support",
        "High-trust action. Reason is mandatory. Sessions are time-boxed.",
    ),
    CapabilitySpec(
        "support.impersonation.end_any",
        "End any user's impersonation session",
        "support",
        "Self-end is always allowed; this covers ending another support user's session.",
    ),
]


# Quick self-check: every code must be unique. Caught at import time so
# mistakes don't survive to a migration run.
_codes = [c.code for c in CAPABILITIES]
if len(_codes) != len(set(_codes)):
    dupes = {c for c in _codes if _codes.count(c) > 1}
    raise RuntimeError(f"Duplicate capability codes in registry: {sorted(dupes)}")


def all_codes() -> list[str]:
    """Return every capability code the platform knows about."""
    return [c.code for c in CAPABILITIES]


def by_domain() -> dict[str, list[CapabilitySpec]]:
    """Group the registry by domain prefix for UI display.

    Returns a dict keyed by domain, with values sorted by code. Insertion
    order reflects the order caps appear in the registry — which is
    itself ordered to match spec §10.3.
    """
    out: dict[str, list[CapabilitySpec]] = {}
    for cap in CAPABILITIES:
        out.setdefault(cap.domain, []).append(cap)
    return out
