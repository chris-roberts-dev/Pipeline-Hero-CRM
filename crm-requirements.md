# MyPipelineHero CRM
## Product Requirements & Architecture Specification

**Document status:** Revised baseline
**Prepared for:** MyPipelineHero CRM Development  
**Primary stack baseline:** Django 5.2+, Python 3.14, PostgreSQL 17, Docker-first architecture  
**Document purpose:** Define the confirmed requirements, recommended system layout, phased roadmap, and implementation guardrails for a multi-tenant Django CRM that supports leads, quoting, clients, services, resale products, in-house manufactured products, purchasing, work execution, and invoicing.

---

## 1. Executive Summary

MyPipelineHero will be a **multi-tenant CRM and operations platform** built in **Django 5.2+** with **Python 3.14**, **PostgreSQL 17**, and **Docker from the first commit forward**. The system will support both:

- **services rendered** to clients, and
- **products sold**, including:
  - purchased and resold items, and
  - custom products built in-house.

The core commercial workflow is:

**Lead → Quote → Acceptance → Client / Sales Order → Fulfillment Artifacts → Invoice**

Fulfillment artifacts must support:

- **Work Orders** for services,
- **Purchase Orders** for bought-and-resold items,
- **Build Orders** for in-house custom products.

The application will use **row-based multi-tenancy**, a **custom email-first user model**, **global support/super-admin users**, **organization-scoped membership and RBAC**, a **central marketing/login site**, and **tenant subdomain portals** under the pattern:

`{slug}.mypipelinehero.com`

The Django admin will exist as an **internal platform/configuration console**, not the primary business-user application. Tenant-facing workflows should live in the main CRM application UI.

---

## 2. Confirmed Decisions

The following decisions were explicitly confirmed and must be treated as requirements, not suggestions.

### 2.1 Platform and Infrastructure
- Framework: **Django 5.2+**
- Language: **Python 3.14**
- Database: **PostgreSQL 17**
- Containerization: **Docker from project inception**
- Local development: containerized
- Production target: **container platform**

### 2.2 Tenancy and Identity
- Tenancy model: **row-based multi-tenancy**
- Super-admin/support users: **global**
- Normal users: **may belong to multiple organizations**
- Support users must be able to **impersonate tenant users / tenant sessions**
- Tenant routing pattern: **central login** on root domain, then redirect to tenant subdomain

### 2.3 Application Flow
- Post-acceptance object model: **accepted quote must create a Sales Order / Client Order first**
- Service fulfillment: **accepted service lines generate Work Orders / Jobs**
- Cardinality: **one SalesOrderLine generates exactly one WorkOrder** 
- Product fulfillment:
  - resale items generate **Purchase Orders** as needed
  - in-house custom items generate **Build Orders**

### 2.4 Commercial and Operations Scope
- Pricing engine: **structured pricing engine required — strategy pattern by line type** 
- Manufacturing scope: **Build Orders + BOM + labor/material actual costing**
- BOM versioning: **effective-from date versioning; Build Orders reference a specific BOM version**
- Client model: **customer hierarchy with billing account, contacts, and multiple locations/sites**
- Client matching on acceptance: **user explicitly selects existing client or confirms new client creation before acceptance proceeds** (resolved — LF-03)
- Acceptance: **internal status transition only** for initial implementation
- Billing: **include invoicing and payment tracking, but not full accounting**

### 2.5 UI / Admin Direction
- Application posture: **server-rendered Django first**
- Admin direction: **Django admin for internal platform/configuration, not primary business workflows**
- Main site requirement: **marketing/landing page with central login**
- Tenant users are routed to `https://{slug}.mypipelinehero.com`

### 2.6 Authorization
- RBAC model: **org-scoped roles + capability-level grants + support/super-admin exceptions**
- Platform must ship with **default roles/capabilities**
- Tenants must be able to **define additional roles/capabilities**

### 2.7 Session Management
- A user may have **one active tenant session per browser context at a time**
- Opening a second tenant subdomain in the same browser does not invalidate the first session but does not inherit context from it

### 2.8 Implementation Architecture Decisions
- Cross-subdomain auth/session strategy: **short-lived, signed, single-use token handoff from root domain to tenant subdomain**
- Async worker stack: **Celery + Redis**
- Local subdomain development: **reverse proxy + wildcard local domain support**
- Document/media storage:
  - **local filesystem** for dev/test
  - **S3-compatible object storage** for non-dev environments
- Monitoring baseline:
  - **structured JSON logging**
  - **Sentry** for application and worker error monitoring
  - **OpenTelemetry optional later** if distributed tracing needs expand
- Accounting integration posture: **define an adapter/integration boundary now; defer product selection until later**
- Scheduling/dispatch posture: **basic work-order assignment/scheduling in the current phase; advanced dispatch/routing deferred**

---

## 3. Product Goals

### 3.1 Primary Goals
1. Provide a single platform to manage the lifecycle from lead intake to fulfillment and invoice.
2. Support multiple tenant organizations in one deployment without data leakage.
3. Support mixed quotes and orders containing:
   - services,
   - resale products,
   - manufactured/custom-built products.
4. Support tenant-specific roles, pricing logic, and operational workflows.
5. Provide a professional SaaS experience with a root marketing/login site and branded tenant portals.
6. Support growth from a server-rendered monolith into a more modular platform over time.

### 3.2 Non-Goals for Initial Release
The following are intentionally out of scope unless later approved:
- Full double-entry accounting / general ledger
- Full warehouse management system functionality
- Native e-signature platform implementation
- Native payment processor as system of record for accounting
- Mobile-native applications
- Customer-facing public quote builder
- Schema-per-tenant deployment model

---

## 4. Guiding Principles

1. **Tenant safety over convenience** — no cross-tenant leakage.
2. **Commercial history is immutable enough to audit** — accepted pricing and generated orders must be reproducible.
3. **Workflow objects must reflect operational reality** — quote acceptance alone is not fulfillment.
4. **The admin is not the application** — use admin for back-office/platform tasks; use application screens for operational workflows.
5. **A custom user model is required from day one** — no retrofit later.
6. **Docker is first-class, not an afterthought** — dev, CI, and production workflows must respect this.
7. **Design for role flexibility** — default roles are required, but tenant-specific extensions must be supported.
8. **Build for observability and auditability** — especially impersonation, tenant switching, pricing overrides, and status transitions.

---

## 5. High-Level Architecture

### 5.1 Architectural Style
The platform should be implemented as a **server-rendered Django application** using conventional Django views, templates, forms, and service-layer orchestration.

The implementation should:
- prioritize Django-native patterns,
- keep business logic out of templates and thin views,
- centralize domain workflows in service/application layers,
- allow future API expansion without forcing API-first architecture on v1.

### 5.2 Recommended Architectural Shape
A pragmatic modular monolith is recommended.

Characteristics:
- One deployable Django application
- Bounded apps/domains inside the repository
- Shared PostgreSQL database
- Row-based tenancy enforced consistently
- Background workers for async tasks
- Reverse proxy / ingress routing for root domain and tenant subdomains

### 5.3 Core Domains
- Platform / Identity
- CRM Pipeline
- Catalog / Pricing
- Manufacturing / Procurement / Work Execution
- Billing / Invoicing
- Reporting / Audit / Support

---

## 6. Entity Lifecycle State Machines

Every workflow entity has explicitly defined states and transitions. These definitions are authoritative — implementation must not add, remove, or reorder states or transitions without updating this section first.

**Notation:** System-triggered transitions are initiated by a Celery task or automated process, not a user action. All non-forward transitions that carry a "reason required" note must capture a reason string before the transition is persisted. All transitions produce an AuditEvent.

### 6.1 Lead

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| New | Contacted | first_contact | Sales rep | — |
| Contacted | Qualified | qualify | Sales rep | — |
| Contacted | Unqualified | disqualify | Sales rep / Manager | — |
| Qualified | Converted | convert_to_quote | Sales rep | New QuoteVersion created in DRAFT; lead activity logged |
| Qualified | Unqualified | disqualify | Manager | — |
| Unqualified | Qualified | re_qualify | Manager | — |
| Unqualified | Archived | archive | Any member | — |
| Converted | Archived | archive | Manager | — |

### 6.2 Quote Version

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Draft | Sent | send_quote | Sales rep | Email notification queued (async) |
| Draft | Superseded | new_version_created | Quote editor | New version created in DRAFT; this version locked |
| Sent | Draft | retract_quote | Sales rep | — |
| Sent | Accepted | accept_quote | Authorized (quotes.approve) | SalesOrder created; pricing snapshot frozen; fulfillment artifacts dispatched async |
| Sent | Declined | decline_quote | Authorized user | — |
| Sent | Expired | expiry_check | System — Celery beat, daily | expiration_date has passed |
| Sent | Superseded | new_version_created | Quote editor | New version created in DRAFT |

**Terminal states:** Accepted, Declined, Expired, Superseded — no transitions out.

### 6.3 Sales Order

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Open | Cancelled | cancel_order | Manager (orders.cancel) | Only if no active WO/PO/BuildOrder; reason required |
| Open | In fulfillment | fulfillment_started | System | First fulfillment artifact leaves initial state |
| In fulfillment | Fulfilled | all_fulfillment_complete | System | All WOs/POs/BuildOrders in terminal state |
| In fulfillment | Part. invoiced | partial_invoice_issued | Billing user | Invoice created for subset of order lines |
| Fulfilled | Part. invoiced | partial_invoice_issued | Billing user | — |
| Fulfilled | Invoiced | full_invoice_issued | Billing user | Invoice covers all lines |
| Part. invoiced | Invoiced | remaining_invoiced | Billing user | All remaining lines now invoiced |
| Invoiced | Closed | payment_complete | System | All invoice amounts fully paid |
| Part. invoiced | Closed | payment_complete | System | Outstanding balance fully paid |

**Terminal states:** Cancelled, Closed — no transitions out.

### 6.4 Work Order

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Pending | Assigned | assign | Dispatcher / Manager | Assignee, service location, and scheduled date confirmed |
| Assigned | Pending | unassign | Manager | — |
| Assigned | In progress | start_work | Assigned user / Mgr | — |
| In progress | Completed | complete_work | Assigned user | Outcome notes required; triggers order fulfillment check |
| In progress | On hold | put_on_hold | Assigned user / Mgr | Reason required |
| On hold | In progress | resume_work | Assigned user / Mgr | — |
| Pending | Cancelled | cancel | Manager | Reason required |
| Assigned | Cancelled | cancel | Manager | Reason required |

**Terminal states:** Completed, Cancelled — no transitions out.

### 6.5 Purchase Order

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Draft | Submitted | submit_po | Purchasing user | Sent to supplier |
| Draft | Cancelled | cancel | Purchasing manager | — |
| Submitted | Acknowledged | acknowledge | Purchasing user | Supplier has confirmed the order |
| Submitted | Cancelled | cancel | Purchasing manager | Only before supplier processing; reason required |
| Acknowledged | Part. received | record_receipt | Receiving user | Partial quantity received against PO line(s) |
| Acknowledged | Received | record_receipt | Receiving user | Full quantity received across all lines |
| Part. received | Received | record_receipt | Receiving user | Remaining quantity received; PO complete |

**Terminal states:** Cancelled, Received — no transitions out.

### 6.6 Build Order

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Planned | In progress | start_build | Production user | BOM version snapshot taken; estimated costs locked |
| Planned | Cancelled | cancel | Production manager | Reason required |
| In progress | Quality review | submit_for_review | Production user | QA assignment notification sent |
| In progress | On hold | put_on_hold | Production manager | Reason required; labor clock paused |
| On hold | In progress | resume_build | Production manager | — |
| On hold | Cancelled | cancel | Production manager | Reason required |
| Quality review | Complete | approve_build | QA user | Actual cost finalized; triggers order fulfillment check |
| Quality review | In progress | reject_build | QA user | Rejection notes required; returned for rework |

**Terminal states:** Cancelled, Complete — no transitions out.

### 6.7 Invoice

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Draft | Sent | send_invoice | Billing user | PDF generated async; delivery email queued |
| Draft | Void | void | Billing manager | — |
| Sent | Overdue | overdue_check | System — Celery beat, daily | due_date passed; overdue notification sent to client contact |
| Sent | Part. paid | record_payment | Billing user | Partial amount recorded; balance recalculated |
| Sent | Paid | record_payment | Billing user | Full amount received; triggers SalesOrder → Closed check |
| Sent | Void | void | Billing manager | Reason required; cannot void a paid invoice |
| Overdue | Part. paid | record_payment | Billing user | — |
| Overdue | Paid | record_payment | Billing user | Triggers SalesOrder → Closed check |
| Part. paid | Paid | record_payment | Billing user | Remaining balance paid; triggers SalesOrder → Closed check |

**Terminal states:** Void, Paid — no transitions out.

### 6.8 Membership

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Invited | Active | accept_invite | Invited user | — |
| Invited | Expired | invite_expiry | System — Celery beat | After configured expiry window (default: 7 days) |
| Active | Inactive | deactivate | Org admin / Platform admin | Access revoked immediately; data and history preserved |
| Active | Suspended | suspend | Org admin / Platform admin | Reason required; access blocked; identity preserved for audit |
| Suspended | Active | reinstate | Org admin / Platform admin | — |
| Suspended | Inactive | deactivate | Org admin / Platform admin | — |
| Inactive | Active | reactivate | Org admin / Platform admin | — |

---

## 7. Multi-Tenancy Requirements

### 7.1 Tenancy Model
The system must use **row-based multi-tenancy**.

#### Requirements
- Each tenant is represented by an **Organization** record.
- All tenant-owned records must contain an organization reference.
- Uniqueness constraints for tenant-owned business objects should generally be scoped by organization.
- Global/platform objects must be explicitly separated from tenant-owned objects.
- Support users and super-admins must be able to access multiple tenants without duplicating user accounts.

### 7.2 Organization Context
The application must maintain an active organization context for tenant-bound interactions.

#### Requirements
- A multi-org user must be able to select an organization after central login.
- The chosen organization must determine the portal redirect and active tenant context.
- Tenant-bound requests must validate organization context before data access.
- A user's membership and capability set must be evaluated within the active organization context.

### 7.3 Tenant Isolation Rules
The platform must enforce tenant isolation at multiple layers.

#### Required controls
- Queryset scoping via `TenantQuerySet` and `TenantManager` on all tenant-owned models
- A CI-enforced test that enumerates all models with an `organization` FK and asserts they use `TenantManager`
- Form field / FK choice scoping
- View/service-layer validation
- Object creation safeguards
- Organization-scoped uniqueness constraints
- Automated test coverage for tenant leakage prevention

### 7.4 Super-Admin and Support Access
Support users are global users with cross-tenant access under controlled conditions.

#### Requirements
- Support users may view or enter tenant portals.
- Support users may impersonate tenant sessions.
- Impersonation must require a reason entry.
- Impersonation must be logged in an immutable audit trail.
- The UI must clearly indicate impersonation mode.
- Impersonation sessions must be reversible and attributable to the original support user.
- All actions taken during an impersonation session must be recorded in AuditEvent with both the original support user identity and the impersonated user identity.

---

## 8. Authentication, User Model, and Membership

### 8.1 Custom User Model
A custom user model is mandatory.

#### Requirements
- Email is the primary identifier.
- Email is required.
- Email must be unique at the global user identity level.
- The default Django username field must not be used as the primary identity mechanism.
- Authentication flows must support password-based login initially.

### 8.2 User Relationships
A user may belong to multiple organizations.

#### Required entities
- User
- Organization
- Membership
- Role
- Capability
- MembershipCapabilityGrant or equivalent override structure

### 8.3 Membership Model Requirements
Each membership must support:
- user reference
- organization reference
- role assignment(s)
- membership status
- default landing behavior if multiple orgs exist
- audit metadata

### 8.4 Password Reset / Account Lifecycle
The system must support:
- password reset via email,
- invite flows for new users,
- activation/deactivation of memberships,
- deactivation of users,
- suspension of tenant access without deleting platform identity.

---

## 9. Domain, URL, and Login Flow Requirements

### 9.1 Root Site
The root domain `mypipelinehero.com` must provide:
- public marketing/landing pages,
- login entry point,
- support/admin access entry points as needed,
- organization picker for multi-org users after authentication.

### 9.2 Tenant Portal Domain Pattern
Tenant portals must live under:
- `https://{slug}.mypipelinehero.com`

#### Requirements
- Organization slugs must be unique.
- Slugs must be validated for subdomain safety.
- The request router must resolve tenant subdomains to organizations.
- Invalid, inactive, or unauthorized tenant routes must fail safely.
- The organization slug lookup must be cached (Redis) with explicit cache invalidation on slug/status changes.

### 9.3 Confirmed Login Flow
The required login flow is:
1. User visits `mypipelinehero.com`
2. User authenticates centrally
3. If user belongs to one org, redirect to that org portal
4. If user belongs to multiple orgs, show org picker
5. Redirect to selected tenant subdomain
6. Establish active tenant session/context

### 9.4 Confirmed Cross-Subdomain Authentication Strategy
The platform must use a **short-lived, signed, single-use token handoff** from the root domain to the tenant subdomain rather than a shared parent-domain tenant session.

#### Required behavior
- Authentication starts on `mypipelinehero.com`.
- After login and org selection, the root domain issues a short-lived handoff ticket/token (maximum 60-second lifetime) for the chosen organization, stored in Redis for single-use invalidation.
- The user is redirected to the tenant portal handoff-completion endpoint on `https://{slug}.mypipelinehero.com`.
- The tenant portal validates the handoff token, establishes a **tenant-local session**, and invalidates the token after first use.
- Handoff tokens must expire quickly, be single use, and fail safely on replay or tampering attempts.
- Logout behavior must be defined for both root-domain and tenant-portal contexts.
- Support-user access and impersonation flows must remain auditable and distinct from ordinary tenant login.
- A shared parent-domain cookie strategy must **not** be used as the primary tenant-session mechanism.

### 9.5 Session Behavior Across Tenants
- A user may have one active tenant session per browser context at a time.
- Opening a second tenant subdomain in the same browser does not invalidate the first session but does not inherit context from it.
- Support impersonation sessions are distinct from the impersonating user's own tenant session.

---

## 10. Authorization and RBAC Requirements

### 10.1 Authorization Model
The platform must support **org-scoped RBAC with capability-level grants**.

### 10.2 Evaluation Algorithm
Permission checks must execute the following steps in order. No step may be skipped.

1. If `user.is_superuser` → grant (short-circuit)
2. If an active impersonation session is present → evaluate capabilities as the impersonated membership; record all actions under the original support user identity
3. Retrieve the user's active Membership for the current organization; if none → deny
4. Collect all capabilities from the membership's assigned Roles via RoleCapability
5. Apply MembershipCapabilityGrant overrides: GRANT overrides add capabilities; DENY overrides remove capabilities and take precedence over role grants
6. If the required capability is in the final set → grant; otherwise → deny
7. For object-level checks: additionally verify the target object belongs to the active organization and that any status-based restrictions are satisfied

### 10.3 Capability Registry
The following 73 capabilities are shipped as system-defined seed data via a data migration. Capability codes follow the pattern `{domain}.{resource}.{action}`.

#### Lead Management (`leads.*`)

| Code | Name | Notes |
|---|---|---|
| `leads.view` | View leads | Required for all lead list/detail access |
| `leads.create` | Create leads | |
| `leads.edit` | Edit leads | Own leads only by default; object-level ownership check applies |
| `leads.edit_any` | Edit any lead | Overrides ownership restriction |
| `leads.archive` | Archive leads | |
| `leads.convert` | Convert lead to quote | Requires `quotes.create` also |
| `leads.assign` | Assign lead ownership | |

#### Quote Management (`quotes.*`)

| Code | Name | Notes |
|---|---|---|
| `quotes.view` | View quotes | |
| `quotes.create` | Create quotes / new versions | |
| `quotes.edit` | Edit draft quotes | Status check: DRAFT only |
| `quotes.send` | Send quote to client | Status check: DRAFT only |
| `quotes.retract` | Retract a sent quote | Status check: SENT only |
| `quotes.approve` | Accept / approve a quote | Internal acceptance; highest-trust action |
| `quotes.decline` | Mark quote declined | |
| `quotes.line.override_price` | Override line item price | Audit event required |
| `quotes.line.apply_discount` | Apply discount to line or quote | |
| `quotes.delete_draft` | Delete a draft quote version | Hard delete; only DRAFT versions |

#### Client Management (`clients.*`)

| Code | Name | Notes |
|---|---|---|
| `clients.view` | View client records | |
| `clients.create` | Create new clients | Also triggered by quote acceptance flow |
| `clients.edit` | Edit client details | |
| `clients.merge` | Merge duplicate client records | High-risk; restricted to managers |
| `clients.deactivate` | Deactivate a client | |
| `clients.contacts.manage` | Add/edit/remove client contacts | |
| `clients.locations.manage` | Add/edit/remove client locations | |

#### Sales Order Management (`orders.*`)

| Code | Name | Notes |
|---|---|---|
| `orders.view` | View sales orders | |
| `orders.edit` | Edit order notes/metadata | Commercial lines are immutable post-acceptance |
| `orders.cancel` | Cancel an order | Only if no active fulfillment artifacts; reason required |
| `orders.generate_fulfillment` | Manually trigger fulfillment artifact generation | Normally system-triggered |

#### Catalog Management (`catalog.*`)

| Code | Name | Notes |
|---|---|---|
| `catalog.view` | View catalog items | Needed for quote line item selection |
| `catalog.services.manage` | Create/edit/deactivate services | |
| `catalog.products.manage` | Create/edit/deactivate products | |
| `catalog.materials.manage` | Create/edit/deactivate raw materials | |
| `catalog.suppliers.manage` | Create/edit/deactivate suppliers | |
| `catalog.bom.manage` | Create/edit BOMs and BOM lines | |
| `catalog.pricing_rules.manage` | Create/edit pricing rules | |
| `catalog.pricing_rules.view` | View pricing rules | Needed for quote pricing transparency |

#### Work Order Management (`workorders.*`)

| Code | Name | Notes |
|---|---|---|
| `workorders.view` | View work orders | |
| `workorders.assign` | Assign/unassign work orders | |
| `workorders.update_status` | Update work order status | Must be assignee OR have `workorders.manage` |
| `workorders.manage` | Full work order management | Includes cancel / reassign / override |
| `workorders.complete` | Mark work order completed | Outcome notes required |
| `workorders.view_all` | View work orders across all assignees | Without this, users only see their own |

#### Purchase Order Management (`purchasing.*`)

| Code | Name | Notes |
|---|---|---|
| `purchasing.view` | View purchase orders | |
| `purchasing.create` | Create POs from order lines | |
| `purchasing.edit` | Edit draft POs | Status check: DRAFT only |
| `purchasing.submit` | Submit PO to supplier | |
| `purchasing.receive` | Record receipt against PO lines | |
| `purchasing.cancel` | Cancel a PO | Status check: before supplier processing |

#### Build Order Management (`build.*`)

| Code | Name | Notes |
|---|---|---|
| `build.view` | View build orders | |
| `build.manage` | Start / hold / resume build orders | |
| `build.labor.record` | Record labor entries | |
| `build.labor.edit_any` | Edit any user's labor entries | Managers only |
| `build.qa.review` | Approve or reject builds in quality review | |
| `build.cost.view` | View estimated vs actual cost analysis | May be restricted by sensitivity |

#### Invoicing and Billing (`billing.*`)

| Code | Name | Notes |
|---|---|---|
| `billing.view` | View invoices and payments | |
| `billing.invoice.create` | Create invoices from orders | |
| `billing.invoice.send` | Send invoice to client | |
| `billing.invoice.void` | Void an invoice | Cannot void a PAID invoice |
| `billing.payment.record` | Record payment against invoice | |
| `billing.payment.edit` | Edit a recorded payment | High sensitivity |
| `billing.reports.view` | View billing reports and balance summaries | |

#### Reporting (`reporting.*`)

| Code | Name | Notes |
|---|---|---|
| `reporting.view` | Access standard reports | |
| `reporting.export` | Export report data | |
| `reporting.advanced` | Access cost analysis and margin reports | Sensitive; restricted |

#### Tenant Administration (`admin.*`)

| Code | Name | Notes |
|---|---|---|
| `admin.members.view` | View org members and roles | |
| `admin.members.invite` | Invite new members | |
| `admin.members.deactivate` | Deactivate a membership | |
| `admin.members.suspend` | Suspend a membership | |
| `admin.roles.view` | View role definitions | |
| `admin.roles.manage` | Create/edit org-defined roles | |
| `admin.roles.assign` | Assign roles to members | |
| `admin.capabilities.grant` | Grant per-membership capability overrides | |
| `admin.org.settings` | Edit org settings (name / logo / timezone etc.) | |
| `admin.numbering.configure` | Configure entity numbering prefixes | |

### 10.4 Default Role Definitions
These roles must be seeded via a data migration before the first production release. They are organization-scoped — each organization gets its own copies so tenants can customize assignments.

| Role | Intended For | Key Capabilities Included |
|---|---|---|
| Owner | Tenant account owner | All capabilities |
| Org Admin | Office/operations manager | All except platform-level actions |
| Regional Manager | Regional level managers | All except platform-level actions; restricted to their region |
| Market Manager | Market level managers | All except platform-level actions; restricted to their market |
| Location Manager | Location level managers | All except platform-level actions; restricted to their location |
| Sales Staff | Salespeople | `leads.*`, `quotes.view/create/edit/send`, `clients.view/create/edit`, `orders.view`, `catalog.view` |
| Service Staff | Field service worker | `workorders.view`, `workorders.update_status`, `workorders.complete` — own WOs only |
| Production Staff | Shop floor | `build.view`, `build.manage`, `build.labor.record` — own build orders only |
| Viewer | Read-only stakeholder | `*.view` capabilities only, no mutations |

**Customization rule:** Tenants may create new roles and assign any system-defined capabilities to them. They may not modify the seeded default roles (those are read-only templates). Tenants may modify role assignments for their own members freely via the org admin UI.

### 10.5 RBAC Enforcement Matrix
The following matrix maps every view and action to its queryset scope, required capability, object-level check, and audit event. Every row is an enforced requirement.

**Three-layer rule:** Queryset scoping, view-level capability check, and object-level state/ownership check are all required. No layer substitutes for another.

#### Lead Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Lead list | `for_org(org)` | `leads.view` | — | — |
| Lead detail | `for_org(org)` | `leads.view` | — | — |
| Create lead | `for_org(org)` | `leads.create` | — | `LEAD_CREATED` |
| Edit lead | `for_org(org)` | `leads.edit` | `lead.owner == user` unless `leads.edit_any` | `LEAD_UPDATED` |
| Archive lead | `for_org(org)` | `leads.archive` | status not already ARCHIVED | `LEAD_ARCHIVED` |
| Assign lead | `for_org(org)` | `leads.assign` | — | `LEAD_ASSIGNED` |
| Convert to quote | `for_org(org)` | `leads.convert` + `quotes.create` | `lead.status == QUALIFIED` | `LEAD_CONVERTED` |

#### Quote Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Quote list | `for_org(org)` | `quotes.view` | — | — |
| Quote detail | `for_org(org)` | `quotes.view` | — | — |
| Create quote / new version | `for_org(org)` | `quotes.create` | if new version: existing version status != ACCEPTED | `QUOTE_VERSION_CREATED` |
| Edit quote line | `for_org(org)` | `quotes.edit` | `version.status == DRAFT` | `QUOTE_LINE_UPDATED` |
| Override line price | `for_org(org)` | `quotes.line.override_price` | `version.status == DRAFT` | `QUOTE_LINE_PRICE_OVERRIDE` |
| Apply discount | `for_org(org)` | `quotes.line.apply_discount` | `version.status == DRAFT` | `QUOTE_DISCOUNT_APPLIED` |
| Send quote | `for_org(org)` | `quotes.send` | `version.status == DRAFT` | `QUOTE_SENT` |
| Retract quote | `for_org(org)` | `quotes.retract` | `version.status == SENT` | `QUOTE_RETRACTED` |
| Accept quote | `for_org(org)` | `quotes.approve` | `version.status == SENT` | `QUOTE_ACCEPTED` |
| Decline quote | `for_org(org)` | `quotes.decline` | `version.status == SENT` | `QUOTE_DECLINED` |
| Delete draft | `for_org(org)` | `quotes.delete_draft` | `version.status == DRAFT` | `QUOTE_DRAFT_DELETED` |

#### Client Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Client list | `for_org(org)` | `clients.view` | — | — |
| Client detail | `for_org(org)` | `clients.view` | — | — |
| Create client | `for_org(org)` | `clients.create` | — | `CLIENT_CREATED` |
| Edit client | `for_org(org)` | `clients.edit` | `client.status == ACTIVE` | `CLIENT_UPDATED` |
| Deactivate client | `for_org(org)` | `clients.deactivate` | — | `CLIENT_DEACTIVATED` |
| Manage contacts | `for_org(org)` | `clients.contacts.manage` | — | `CLIENT_CONTACT_UPDATED` |
| Manage locations | `for_org(org)` | `clients.locations.manage` | — | `CLIENT_LOCATION_UPDATED` |
| Merge clients | `for_org(org)` | `clients.merge` | both clients in org | `CLIENT_MERGED` |

#### Sales Order Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Order list | `for_org(org)` | `orders.view` | — | — |
| Order detail | `for_org(org)` | `orders.view` | — | — |
| Edit order notes | `for_org(org)` | `orders.edit` | `order.status` not CANCELLED/CLOSED | `ORDER_NOTES_UPDATED` |
| Cancel order | `for_org(org)` | `orders.cancel` | no active WO/PO/BuildOrder | `ORDER_CANCELLED` |

#### Catalog Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Browse catalog (quote line picker) | `for_org(org)` | `catalog.view` | `item.is_active == True` | — |
| Service list / detail | `for_org(org)` | `catalog.view` | — | — |
| Create / edit service | `for_org(org)` | `catalog.services.manage` | — | `CATALOG_SERVICE_SAVED` |
| Create / edit product | `for_org(org)` | `catalog.products.manage` | — | `CATALOG_PRODUCT_SAVED` |
| Create / edit raw material | `for_org(org)` | `catalog.materials.manage` | — | `CATALOG_MATERIAL_SAVED` |
| Create / edit supplier | `for_org(org)` | `catalog.suppliers.manage` | — | `CATALOG_SUPPLIER_SAVED` |
| Create / edit BOM | `for_org(org)` | `catalog.bom.manage` | — | `CATALOG_BOM_SAVED` |
| View pricing rules | `for_org(org)` | `catalog.pricing_rules.view` | — | — |
| Create / edit pricing rules | `for_org(org)` | `catalog.pricing_rules.manage` | — | `PRICING_RULE_SAVED` |

#### Work Order Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| WO list | `for_org(org)` filtered by assignee unless `workorders.view_all` | `workorders.view` | — | — |
| WO detail | `for_org(org)` | `workorders.view` | must be assignee unless `workorders.view_all` | — |
| Assign WO | `for_org(org)` | `workorders.assign` | `WO.status` in {PENDING, ASSIGNED} | `WO_ASSIGNED` |
| Update WO status | `for_org(org)` | `workorders.update_status` | must be assignee unless `workorders.manage` | `WO_STATUS_CHANGED` |
| Complete WO | `for_org(org)` | `workorders.complete` | `WO.status == IN_PROGRESS`; outcome notes present | `WO_COMPLETED` |
| Cancel WO | `for_org(org)` | `workorders.manage` | `WO.status` not COMPLETED | `WO_CANCELLED` |

#### Purchase Order Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| PO list | `for_org(org)` | `purchasing.view` | — | — |
| PO detail | `for_org(org)` | `purchasing.view` | — | — |
| Create PO | `for_org(org)` | `purchasing.create` | source order line is RESALE type | `PO_CREATED` |
| Edit PO | `for_org(org)` | `purchasing.edit` | `PO.status == DRAFT` | `PO_UPDATED` |
| Submit PO | `for_org(org)` | `purchasing.submit` | `PO.status == DRAFT` | `PO_SUBMITTED` |
| Record receipt | `for_org(org)` | `purchasing.receive` | `PO.status` in {ACKNOWLEDGED, PART_RECEIVED} | `PO_RECEIPT_RECORDED` |
| Cancel PO | `for_org(org)` | `purchasing.cancel` | `PO.status` in {DRAFT, SUBMITTED} | `PO_CANCELLED` |

#### Build Order Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Build order list | `for_org(org)` | `build.view` | — | — |
| Build order detail | `for_org(org)` | `build.view` | — | — |
| Start build | `for_org(org)` | `build.manage` | `BuildOrder.status == PLANNED` | `BUILD_STARTED` |
| Put on hold | `for_org(org)` | `build.manage` | `BuildOrder.status == IN_PROGRESS` | `BUILD_ON_HOLD` |
| Resume build | `for_org(org)` | `build.manage` | `BuildOrder.status == ON_HOLD` | `BUILD_RESUMED` |
| Submit for QA review | `for_org(org)` | `build.manage` | `BuildOrder.status == IN_PROGRESS` | `BUILD_SUBMITTED_FOR_QA` |
| Approve build (QA) | `for_org(org)` | `build.qa.review` | `BuildOrder.status == QUALITY_REVIEW` | `BUILD_APPROVED` |
| Reject build (QA) | `for_org(org)` | `build.qa.review` | `BuildOrder.status == QUALITY_REVIEW`; rejection notes required | `BUILD_REJECTED` |
| Record labor entry | `for_org(org)` | `build.labor.record` | `BuildOrder.status == IN_PROGRESS` | `BUILD_LABOR_RECORDED` |
| Edit any labor entry | `for_org(org)` | `build.labor.edit_any` | entry belongs to org | `BUILD_LABOR_EDITED` |
| View cost analysis | `for_org(org)` | `build.cost.view` | — | — |

#### Billing Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Invoice list | `for_org(org)` | `billing.view` | — | — |
| Invoice detail | `for_org(org)` | `billing.view` | — | — |
| Create invoice | `for_org(org)` | `billing.invoice.create` | SalesOrder exists; lines to invoice exist | `INVOICE_CREATED` |
| Send invoice | `for_org(org)` | `billing.invoice.send` | `Invoice.status == DRAFT` | `INVOICE_SENT` |
| Void invoice | `for_org(org)` | `billing.invoice.void` | `Invoice.status != PAID` | `INVOICE_VOIDED` |
| Record payment | `for_org(org)` | `billing.payment.record` | `Invoice.status` in {SENT, OVERDUE, PART_PAID} | `PAYMENT_RECORDED` |
| Edit payment | `for_org(org)` | `billing.payment.edit` | — | `PAYMENT_EDITED` |

#### Tenant Admin Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Member list | `for_org(org)` | `admin.members.view` | — | — |
| Invite member | `for_org(org)` | `admin.members.invite` | — | `MEMBER_INVITED` |
| Deactivate membership | `for_org(org)` | `admin.members.deactivate` | Cannot deactivate own membership | `MEMBERSHIP_DEACTIVATED` |
| Suspend membership | `for_org(org)` | `admin.members.suspend` | reason required; cannot suspend own membership | `MEMBERSHIP_SUSPENDED` |
| View roles | `for_org(org)` | `admin.roles.view` | — | — |
| Create / edit role | `for_org(org)` | `admin.roles.manage` | — | `ROLE_SAVED` |
| Assign role to member | `for_org(org)` | `admin.roles.assign` | role belongs to org | `ROLE_ASSIGNED` |
| Grant capability override | `for_org(org)` | `admin.capabilities.grant` | capability is a valid system capability | `CAPABILITY_GRANT_APPLIED` |
| Edit org settings | — | `admin.org.settings` | — | `ORG_SETTINGS_UPDATED` |

---

## 11. Commercial Workflow Requirements

### 11.1 Core Pipeline
The platform must support the lifecycle:

**Lead → Quote → Acceptance → Client / Sales Order → Fulfillment → Invoice / Payment Tracking**

### 11.2 Lead Requirements
The system must support leads as pre-client commercial opportunities.

#### Minimum lead capabilities
- create, edit, archive leads
- store lead source
- store primary and secondary contacts
- store notes and internal activity
- store service/site location data
- assign ownership
- track status and stage per state machine (Section 6.1)
- convert lead into quote(s)

### 11.3 Quote and Quote Versioning
Quotes must support mixed commercial lines and multiple versions.

#### Quote container model
The versioning model uses a parent Quote container with child QuoteVersion records:

```
Quote (container)
  ├── id, organization, lead, client, quote_number
  └── QuoteVersion (many)
        ├── id, quote (FK), version_number, status
        ├── expiration_date, subtotal, discount, total
        └── QuoteVersionLine (many)
```

- A Quote holds the stable quote number and org/lead/client references.
- A QuoteVersion holds the working state, status, expiration, and line items.
- Only one QuoteVersion per Quote may be in ACCEPTED status.
- Creating a new version sets the previous version to SUPERSEDED.

#### Required features
- Multiple quote versions per quote container
- Draft/save/send states per version (see state machine, Section 6.2)
- Expiration date per version
- Line items of different types per version
- Discounts at line and quote level
- Notes / terms
- Tenant-specific entity numbering (prefix-configurable; sequence managed by system)
- Pricing snapshots per line item
- Manual price overrides where authorized (requires `quotes.line.override_price`)
- Internal acceptance transition only

#### Quote-level discount rule
Quote-level discount takes precedence over line-level discount when both are present.

### 11.4 Accepted Quote Behavior
Acceptance must not directly create procurement/build artifacts without an order layer.

#### Required behavior on acceptance (REQ-CRM-ACCEPT-01)
1. **Client resolution (must complete before acceptance proceeds):**
   - If the quote is linked to a lead with no associated client: the system prompts the user to confirm creation of a new Client (pre-populated from lead data) or to search for and explicitly select an existing Client.
   - If the quote already references an existing Client: no client creation occurs; the existing client is used directly.
   - Client resolution must succeed before the acceptance status transition completes.
2. **Sales Order creation:** A new SalesOrder is created with status OPEN, referencing the accepted QuoteVersion and the resolved Client. Each accepted QuoteVersionLine is copied to a SalesOrderLine.
3. **Pricing snapshot freezing:** PricingSnapshot records linked to accepted QuoteVersionLines are marked immutable. Catalog or rule changes after acceptance must not alter stored snapshots.
4. **Fulfillment generation (async, via Celery):**
   - SalesOrderLines with `line_type = SERVICE` each trigger creation of exactly one WorkOrder in status PENDING.
   - SalesOrderLines with `line_type = RESALE_PRODUCT` are flagged for Purchase Order generation; PO creation may be completed in the purchasing workflow.
   - SalesOrderLines with `line_type = MANUFACTURED_PRODUCT` each trigger creation of exactly one BuildOrder in status PLANNED, referencing the product's current BOM version.
5. **Idempotency:** Fulfillment generation tasks must be idempotent. Each SalesOrderLine may have at most one WorkOrder, one PurchaseOrder reference, and one BuildOrder.
6. **Audit event:** `QUOTE_ACCEPTED` is recorded with actor, QuoteVersion reference, Client reference, SalesOrder ID, and IDs of all generated fulfillment artifacts.

### 11.5 Client Requirements
Clients are long-lived customer entities, not merely converted leads.

#### Required support
- billing account
- multiple contacts
- multiple service/delivery/install locations
- history of orders, quotes, invoices, and communications
- active/inactive status
- tenant-scoped uniqueness and searchability

### 11.6 Sales Order Requirements
The Sales Order is the operational anchor after acceptance.

#### Required functions
- represent the accepted commercial commitment
- hold order-level status (see state machine, Section 6.3)
- group mixed line types
- drive fulfillment generation
- support invoicing linkage
- support order-level notes and audit history
- preserve accepted commercial terms

### 11.7 Change and Revision Considerations
The platform must be built in a way that can support future change-order functionality.

The initial release should at minimum preserve:
- quote version history,
- accepted order snapshot history,
- audit trail of post-acceptance edits.

---

## 12. Services, Products, and Fulfillment Requirements

### 12.1 Supported Sellable Types
The platform must support at least three sellable categories:
- services
- resale products
- manufactured/custom products

### 12.2 Services
Services represent work performed for the client.

#### Requirements
- services must be definable in the catalog
- service lines must be quotable
- accepted service lines must generate exactly one Work Order per SalesOrderLine
- service pricing must support default logic plus overrides as allowed
- service execution status must be tracked separately from commercial status

### 12.3 Resale Products
Resale products are purchased externally and sold to the client.

#### Requirements
- products must be definable in the catalog
- suppliers/vendors must be supported
- supplier-product associations must be supported
- accepted resale lines must be able to generate Purchase Orders as needed
- pricing must support markup, discounts, and manual overrides by authorized users

### 12.4 Manufactured / In-House Products
Manufactured products are built internally.

#### Requirements
- support product definitions for in-house builds
- support Bill of Materials (BOM) with effective-from date versioning
- support material cost capture
- support labor actual capture
- support Build Orders — one per accepted SalesOrderLine of manufactured type
- support actual-vs-estimated cost comparison
- support downstream service/install linkage where needed

### 12.5 Mixed Orders
A single accepted order may contain multiple line types.

#### Requirements
- one order may generate zero, one, or many downstream artifacts
- generation rules must be line-aware
- generation outcomes must remain traceable back to the source order lines
- generation tasks must be idempotent

---

## 13. Pricing and Costing Requirements

### 13.1 Pricing Engine Architecture
The platform must implement a **strategy pattern by line type** pricing engine.

#### Design
```
PricingContext → PricingStrategy → PricingResult → PricingSnapshot
```

- **PricingContext:** Immutable data object carrying all pricing inputs (line type, catalog references, quantities, costs, rule parameters, customer/tenant configuration). Constructed by a `PricingContextBuilder` that performs all database queries before invoking the engine.
- **PricingStrategy:** One implementation per line type, sharing a common interface. Strategies are pure functions — they do not access the database.
- **PricingResult:** Immutable data object carrying the full price breakdown: base cost, markup, discount, final unit price, override status, and all inputs/outputs for snapshotting.
- **PricingSnapshot:** The database record of a `PricingResult`. Written once at quote time. Never mutated.

**The engine is invoked from the service layer only.** It is never called from a view, a model `save()`, or a template.

#### Line type pricing inputs

| Line Type | Primary Cost Driver | Markup Basis | Key Complication |
|---|---|---|---|
| Service | Flat catalog price (v1) | Catalog default or manual | Discounts, authorized overrides |
| Resale product | Supplier unit cost | Markup % over supplier cost | Supplier price volatility, multiple suppliers |
| Manufactured product | SUM(BOM material costs) | Markup % over total material cost | Multi-component BOM |

#### Confirmed formula for manufactured products
```
Sales Price = [SUM(cost of materials) × (1 + markup %)] - discounts
```

#### Shared override and discount layer
A shared layer sits above all three strategies and applies discounts and authorized price overrides after the strategy returns its base result. This logic is written once and applies identically to all line types.

#### Resolved pricing decisions

| Decision | Resolution |
|---|---|
| Markup resolution precedence | Item-specific rule overrides line-type default |
| Discount stacking | Quote-level discount takes precedence over line-level |
| Negative markup | Allowed at zero; negative blocked at PricingRule validation layer |
| Supplier selection (resale) | User selects supplier in quote line UI; builder receives explicit choice |
| Zero-cost BOM | Raise validation error; a manufactured product with no BOM lines cannot be priced |
| Snapshot version field | `engine_version = '1.0'` field included on PricingSnapshot from the start |

### 13.2 Costing Requirements
The system must support:
- estimated material cost
- actual material cost
- estimated labor cost
- actual labor cost
- comparison between estimated and actual cost at build/order level

### 13.3 Snapshot Requirement
The system must preserve pricing snapshots for:
- quote version lines
- accepted quotes/orders
- invoicing references where needed

Catalog or cost changes after acceptance must not silently rewrite historical commercial records. PricingSnapshot records are written once and never updated; superseded snapshots from re-pricing are retained with `is_active = False`.

### 13.4 Extensibility
The pricing/costing architecture must not block future support for:
- labor-based formulas for services
- overhead allocation
- tiered quantity pricing
- bundles/packages
- customer-specific pricing lists

These are not required in v1 but the strategy pattern architecture specifically accommodates them.

---

## 14. Procurement Requirements

### 14.1 Purchase Orders
The platform must support Purchase Orders for bought-and-resold items.

#### Required features
- create PO from accepted order lines
- associate PO with vendor/supplier
- track PO status (see state machine, Section 6.5)
- record ordered quantities/prices
- support partial fulfillment in the data model
- link PO lines back to source order lines

### 14.2 Raw Material Cost Support
The system must support raw material cost data sufficient for pricing and build costing.

#### Minimum requirements
- raw material product definitions
- supplier linkage where needed
- current cost reference
- historical costing traceability where feasible
- BOM consumption logic support in build costing

### 14.3 Deferred but Related Area
Full inventory management is not required in the current phase. The data model should avoid blocking future inventory expansion.

---

## 15. Manufacturing / Build Requirements

### 15.1 Build Orders
Build Orders are required for custom/in-house product development.

#### Required features
- create Build Orders from accepted order lines (one per SalesOrderLine of manufactured type)
- support status lifecycle (see state machine, Section 6.6)
- attach BOM version reference at creation time; snapshot BOM at build start
- track estimated material/labor
- track actual material/labor
- record completion state
- link finished build output back to source order lines

### 15.2 BOM Requirements
The platform must support BOM definitions for manufactured products with version history.

#### BOM versioning strategy
- BOMs use effective-from date versioning.
- Each BOM version is immutable once active.
- Build Orders reference the specific BOM version active at the time the build is started.
- The BOM version snapshot is taken at `start_build` (when the Build Order transitions from PLANNED to IN PROGRESS), not at quote time.
- Old BOM versions remain accessible for audit and cost comparison.

#### BOM support must include
- parent manufactured product
- BOM version with effective-from date
- material components
- quantities
- units of measure
- cost references per component

### 15.3 Labor Tracking Requirements
The platform must support labor tracking for actual costing.

#### Minimum support
- labor entries against build orders
- user attribution
- duration/hours
- rate or applied labor cost source
- actual cost contribution

### 15.4 Build Cost Analysis
The system must support:
- estimated cost at quote/order time
- actual cost at execution time
- variance reporting (actual minus estimated, by category)

---

## 16. Work Order / Job Requirements

### 16.1 Work Orders Are Required
Accepted service lines must generate Work Orders / Jobs. **One SalesOrderLine of service type generates exactly one WorkOrder**.

### 16.2 Minimum Work Order Capabilities
- create from order line (one-to-one with SalesOrderLine of service type)
- assign ownership/crew/user
- track status (see state machine, Section 6.4)
- track service location
- track planned vs completed work
- store notes/outcomes (outcome notes required to complete)
- maintain linkage to originating order line

### 16.3 Future-Friendly Design
The work-order domain should be designed so later expansion is possible for:
- scheduling/dispatch
- checklists
- recurring service
- route optimization
- completion photos/documents

Those items are not forced into the current phase unless separately approved.

---

## 17. Invoicing and Payment Tracking Requirements

### 17.1 Billing Scope
The platform must include invoicing and payment tracking, but it is **not** required to be a full accounting system.

### 17.2 Required Billing Capabilities
- create invoice records tied to sales orders / fulfillment state
- support invoice statuses (see state machine, Section 6.7)
- support partial invoicing (invoice covering a subset of order lines)
- record amounts due
- record payments received
- track balances outstanding
- maintain client invoice history

### 17.3 Accounting Boundary
The billing domain must remain internally functional for invoicing and payment tracking.

#### Required posture
- The implementation must define a stable adapter/integration boundary so future accounting sync does not require major domain rewrites.
- Client, invoice, and payment models must support external reference IDs, sync status fields, and sync error metadata.
- No external accounting product is selected for v1; selection is intentionally deferred.

---

## 18. Admin and Internal Console Requirements

### 18.1 Admin Purpose
The Django admin must act as an internal platform/configuration console, optimized for:
- platform administration
- tenant administration
- reference data
- support tooling
- audit inspection
- catalog configuration
- selected back-office operations

It should **not** be treated as the main end-user CRM workflow UI.

### 18.2 Custom Admin Site
A custom `AdminSite` implementation is required.

#### Required behavior
- group apps into business-relevant buckets
- display apps/models in custom order
- support organization-aware filtering where appropriate

### 18.3 Recommended Admin Grouping

**Platform**
- Users, Organizations, Memberships, Roles, Capabilities, Audit Events, Impersonation Log

**CRM**
- Leads, Quotes, Clients, Sales Orders, Invoices

**Catalog**
- Services, Products, Raw Materials, BOMs, Suppliers, Pricing Rules

**Operations**
- Purchase Orders, Build Orders, Work Orders

**Reporting**
- Saved reports, snapshots / exports if implemented

### 18.4 Admin Ordering Requirement
Custom app ordering and model ordering must be supported and not left to Django's default alphabetical ordering.

---

## 19. Main Application UI Requirements

### 19.1 Application Experience
The tenant portal must provide business-facing screens for at least:
- dashboard/home
- leads
- quotes
- clients
- orders
- work orders
- purchase orders
- build orders
- invoices

### 19.2 Server-Rendered UI Requirement
The UI should be implemented with server-rendered Django templates/forms unless a later decision explicitly approves a richer client-side stack for specific features.

### 19.3 Root Marketing Site Requirement
The root site must include:
- marketing homepage
- product/feature messaging
- login entry point
- optional contact/demo flow if desired later

### 19.4 Scheduling and Dispatch Boundary
For the current implementation phase, tenant-facing work-order UX must support basic assignment, due/scheduled dates, checklists, notes, and completion tracking. Advanced dispatch capabilities are explicitly deferred.

---

## 20. Background Jobs and Async Processing Requirements

### 20.1 Async Is Required
Background job processing is required from the start.

### 20.2 Expected Async Use Cases
At minimum:
- email sending
- password reset/invite workflows
- invoice/quote PDF generation
- notifications/reminders
- fulfillment artifact generation from accepted quotes
- report exports
- quote expiry processing (Celery beat)
- invoice overdue marking (Celery beat)
- membership invite expiry (Celery beat)

### 20.3 Confirmed Async Stack
**Celery + Redis** for background job processing.

#### Required baseline
- Redis as the broker/backing service
- Celery integrated into Django project and Docker environment from the start
- Retry behavior, failure visibility, and periodic job support from the initial worker design
- All Celery tasks that generate or transition state records must be **idempotent**
- System-triggered state transitions must attribute AuditEvents to a designated system identity (`is_system=True` user), never produce null actor fields

---

## 21. Entity Numbering and Sequencing

### 21.1 Format
All entities with human-facing identifiers must use the format:

`{PREFIX}-{YEAR}-{SEQUENCE}` e.g. `QT-2025-00042`

### 21.2 Rules
- Sequences are per-organization, per-entity-type.
- Sequences are monotonically increasing within a calendar year (resetting annually).
- Tenants may configure the prefix; the system manages the sequence atomically (PostgreSQL sequence or equivalent).
- The following entities each have their own independent sequence: Quote, SalesOrder, PurchaseOrder, BuildOrder, WorkOrder, Invoice.

---

## 22. Data Model Inventory (Recommended)

This section defines the recommended model inventory for planning purposes. Names may vary slightly in implementation, but the domain concepts should remain substantially equivalent.

### 22.1 Platform / Identity

**User:** email, password hash, is_active, is_staff, is_superuser, is_system, timestamps

**Organization:** name, slug, status, timezone, timestamps

**Membership:** user, organization, status, role assignments, default flags, timestamps

**Role:** organization (nullable for system roles), code, name, description, timestamps

**Capability:** code, name, category/group, description, timestamps

**RoleCapability:** role, capability

**MembershipCapabilityGrant:** membership, capability, grant_type (GRANT/DENY)

**ImpersonationAuditLog:** acting support user, target membership or user, organization, reason, session_id, start/end timestamps, metadata

**AuditEvent:** organization (nullable), actor, on_behalf_of (nullable — for impersonation), event_type, object reference metadata, before/after data, timestamps

### 22.2 CRM

**Lead:** organization, lead number/code, source, status, owner, summary fields, timestamps

**LeadContact:** lead, name, email, phone, role/title

**LeadLocation:** lead, address fields, location notes

**Quote:** organization, lead (nullable), client (nullable), quote_number, timestamps

**QuoteVersion:** quote (FK), version_number, status, expiration_date, subtotal, discount, total, timestamps

**QuoteVersionLine:** quote_version, line_type, catalog references (nullable by type), description snapshot, quantity, unit price snapshot, discount, total, pricing_snapshot (FK)

**PricingSnapshot:** organization, quote_line (nullable), line_type, is_active, engine_version, inputs (JSON), outputs (JSON), effective_unit_price, effective_line_total, override_applied, created_at, created_by

**Client:** organization, client_number, billing name, status, notes, external_id (for accounting integration), timestamps

**ClientContact:** client, contact details, role/title, flags

**ClientLocation:** client, location name, address fields, type flags (billing/service/install)

**SalesOrder:** organization, client, originating quote version, order_number, status, totals snapshot, external_id, timestamps

**SalesOrderLine:** sales order, source quote version line, line_type, description snapshot, quantity, pricing snapshot fields, fulfillment_status

### 22.3 Catalog

**ServiceCategory:** organization, code, name

**Service:** organization, category, code, name, description, catalog_price, active flag

**Product:** organization, product_type (RESALE/MANUFACTURED), sku/code, name, description, active flag

**RawMaterial:** organization, sku/code, name, unit of measure, current_cost, active flag

**Supplier:** organization, name, contact fields, status

**SupplierProduct:** organization, supplier, product or raw material reference, supplier_sku, default_cost, lead time fields

**BOM:** organization, finished product, version, effective_from date, status (DRAFT/ACTIVE/SUPERSEDED)

**BOMLine:** bom, raw material, quantity, unit of measure, cost reference

**PricingRule:** organization, rule_type, target_line_type, target_item (nullable — for item-specific rules), parameters (JSON), is_active, priority

### 22.4 Operations

**PurchaseOrder:** organization, supplier, order_number, status, source sales order references, totals, external_id, timestamps

**PurchaseOrderLine:** purchase order, source sales order line, product reference, description snapshot, quantity ordered, quantity received, unit cost

**BuildOrder:** organization, source sales order line, bom (FK — specific version), status, estimated material cost, actual material cost, estimated labor cost, actual labor cost, timestamps

**BuildLaborEntry:** build order, user, hours/duration, applied rate/cost, notes, timestamps

**WorkOrder:** organization, source sales order line, client, client location, status, assigned user, scheduled date, completed date, outcome notes

### 22.5 Billing

**Invoice:** organization, client, sales order, invoice_number, status, total_amount, amount_paid, balance_due, due_date, external_id, sync_status, sync_error, timestamps

**InvoiceLine:** invoice, source order line reference, description snapshot, quantity, unit price, total

**Payment:** organization, client, invoice, amount, payment_date, method, reference, external_id, notes

---

## 23. Recommended Django Project Layout

```text
mypipelinehero/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── dev.py
│       ├── test.py
│       └── prod.py
├── apps/
│   ├── platform/
│   │   ├── accounts/
│   │   ├── organizations/
│   │   ├── rbac/
│   │   ├── audit/
│   │   └── support/
│   ├── web/
│   │   ├── marketing/
│   │   ├── auth_portal/
│   │   └── tenant_portal/
│   ├── crm/
│   │   ├── leads/
│   │   ├── quotes/
│   │   ├── clients/
│   │   ├── orders/
│   │   └── billing/
│   ├── catalog/
│   │   ├── services/
│   │   ├── products/
│   │   ├── materials/
│   │   ├── suppliers/
│   │   ├── pricing/
│   │   └── manufacturing/
│   ├── operations/
│   │   ├── purchasing/
│   │   ├── build/
│   │   └── workorders/
│   └── common/
│       ├── admin/
│       ├── tenancy/
│       ├── db/
│       ├── services/
│       ├── utils/
│       ├── choices/
│       └── tests/
├── templates/
├── static/
├── media/
├── requirements/
├── docker/
│   ├── django/
│   ├── postgres/
│   ├── nginx/
│   └── workers/
├── compose.yaml
└── .env.example
```

---

## 24. Docker-First Requirements

### 24.1 Docker From Day One
The project must be containerized from inception.

### 24.2 Minimum Local Containers
- Django web container
- PostgreSQL 17 container
- Redis container
- Celery worker container
- Nginx reverse proxy container with wildcard local subdomain routing
- pgBouncer container for connection pooling

### 24.3 Environment Requirements
The Docker-based environment must support:
- local development
- automated tests
- migration execution
- seed/bootstrap scripts
- background workers

### 24.4 Configuration Requirements
- Environment variables must drive config
- A checked-in `.env.example` is required
- Secrets must not be committed
- Per-environment settings modules must be supported

### 24.5 Confirmed Subdomain Development Strategy
Local development must include a reverse-proxy-based wildcard local domain strategy. Developers must be able to access the marketing/login site and tenant portals locally using distinct hostnames. The chosen local domain pattern must be documented in onboarding/setup instructions.

### 24.6 Document and Media Storage Strategy
- Dev/test environments: local filesystem-backed storage
- Non-dev environments: **S3-compatible object storage** via `django-storages`
- The database stores file metadata and object references, not binary document contents
- Tenant-bound document access must be permission-aware
- Generated quote/invoice PDFs, completion photos, and uploaded files must use the same storage abstraction

---

## 25. Database and Migration Requirements

### 25.1 PostgreSQL Requirements
Target: PostgreSQL 17

### 25.2 Migration Discipline
- Use Django migrations for schema changes
- Establish custom user model before first production migration baseline
- Prefer additive, reversible migrations where possible
- Avoid casual breaking changes to tenant-critical tables

### 25.3 Indexing Requirements
Indexes must be planned for:
- organization + status
- organization + created_at
- organization + code/number
- subdomain/org slug lookup
- membership lookups
- PricingSnapshot organization + quote_line + is_active

### 25.4 Constraint Requirements
Use database constraints to reinforce:
- org-scoped uniqueness
- required foreign keys
- entity number uniqueness per org

### 25.5 Soft Delete Policy
Commercial records must not be hard-deleted. The following policy applies by entity:

| Entity | Permitted deletion | Policy |
|---|---|---|
| Lead | Soft archive only | Use ARCHIVED status |
| QuoteVersion | DRAFT only | Hard delete of DRAFT; all others immutable |
| Quote container | Never | Preserved for history |
| SalesOrder | Never | Use CANCELLED status |
| Client | Soft deactivate only | Use INACTIVE status |
| Invoice | Never | Use VOID status |
| PricingSnapshot | Never | `is_active` flag only; old snapshots retained |
| BuildOrder / WorkOrder / PurchaseOrder | Never | Use CANCELLED status |

---

## 26. Audit, Security, and Compliance Requirements

### 26.1 Auditability
The system must maintain audit coverage for:
- authentication events
- org selection / switching
- impersonation start/end
- quote acceptance
- pricing overrides
- sales order creation
- PO/build/work-order generation
- invoice/payment updates
- role/capability changes
- all state transitions on workflow entities

### 26.2 Security Requirements
- No tenant data leakage across organizations
- Proper CSRF/session protections
- Principle of least privilege for roles
- Support-user activity must be attributable
- Sensitive admin/support actions must be logged
- Rate limiting on login, password reset, and invite endpoints

### 26.3 Support Access Controls
- Impersonation must be intentional, not silent
- Impersonation banner must be visible throughout impersonation session
- Exit impersonation must restore original context
- Support access should be permission-gated

---

## 27. Testing Requirements

### 27.1 Minimum Testing Scope
The project must include automated tests for:
- tenant isolation (CI-enforced: all tenant models use TenantManager)
- auth and membership flows
- org selection and redirect flow
- quote-to-order conversion
- PO/build/work-order generation
- pricing calculations (unit tests with known inputs and expected outputs)
- pricing snapshot replay (replay must match original calculation)
- RBAC enforcement (capability coverage test: every URL pattern has a required_capability or is explicitly exempted)
- impersonation safeguards and audit attribution
- invoice/payment tracking basics
- state machine transition validity (invalid transitions must be rejected)

### 27.2 Test Layers
- unit tests (especially pricing engine — pure function, no DB required)
- service/domain workflow tests
- integration tests
- admin tests for critical customizations
- end-to-end smoke tests for major workflows

### 27.3 High-Risk Test Areas
- Cross-tenant leakage prevention
- Accepted quote snapshot integrity
- Role/capability enforcement by org
- Support impersonation audit logging with correct actor/on_behalf_of attribution
- Idempotency of fulfillment generation tasks

---

## 28. Observability and Operations Requirements

### 28.1 Minimum Operational Visibility
- structured JSON logging
- application error monitoring (Sentry)
- worker error monitoring (Sentry)
- basic health checks
- migration visibility in deployment workflows

### 28.2 Confirmed Monitoring Baseline
- Structured JSON logging for application and worker processes
- **Sentry** integration for web and worker exception/error monitoring
- Health endpoints for core services
- OpenTelemetry as optional later expansion

---

## 29. Milestone Plan and Estimated Timing

Estimates assume a single senior full-stack developer. Multiply by 0.6 for a team of three developers.

### Milestone 0 — Pre-Build Design Sprint
**Estimated duration:** 2 weeks

#### Scope
- Confirm and document all state machines (reference Section 6)
- Confirm quote versioning ERD
- Confirm client matching flow
- Confirm entity numbering formats
- Confirm RBAC capability-to-enforcement-point matrix
- Confirm pricing engine architecture decision record
- Confirm BOM versioning decision
- Confirm soft-delete policy by entity type
- Answer all open clarification questions

#### Exit criteria
- No open "or equivalent" ambiguities in any implementation-blocking decision
- State machines signed off by product owner
- Architecture decision records written for pricing engine and quote versioning

### Milestone 1 — Foundation and Platform
**Estimated duration:** 4–6 weeks

#### Scope
- Docker baseline (all containers including pgBouncer and Nginx)
- Django project bootstrap with split settings
- PostgreSQL 17 integration
- Custom user model (`EmailUser`) — migration baseline established
- Organizations and memberships
- RBAC infrastructure: `TenantQuerySet`, `TenantManager`, `evaluate_capability()`, `requires_capability()` decorator, `CapabilityRequiredMixin`
- Handoff token service (Redis-backed, 60-second TTL, single-use)
- Central login flow: authenticate → org picker → token → tenant redirect
- Impersonation flow: initiate (reason required), banner, exit
- ImpersonationAuditLog (write-once enforced)
- AuditEvent model and service (with `on_behalf_of` field for impersonation)
- Custom admin shell: custom AdminSite, Platform group, all models registered
- Celery + Redis integration with retry configuration
- Sentry integration (web + worker)
- Structured JSON logging
- Health check endpoints
- All 73 capabilities and 9 default roles seeded via data migration
- System user record seeded for Celery task attribution
- Entity numbering service (org-scoped sequences)

#### Exit criteria
- User can log in centrally, select org, arrive at tenant subdomain with active session
- Support user can impersonate a tenant user; impersonation is logged and visible in UI
- CI test: all models with `organization` FK use `TenantManager`
- Handoff token replay attack is rejected
- RBAC unit tests pass: grant, deny, override, superuser bypass

### Milestone 2 — CRM Core
**Estimated duration:** 6–8 weeks

#### Scope
- Lead model, CRUD, state machine enforcement
- Lead → Quote conversion
- Quote container + QuoteVersion model (per Section 11.3)
- QuoteVersionLine with three line types (stub pricing for product/manufactured)
- PricingSnapshot model (with engine_version field)
- Quote state machine enforcement
- Client model: billing account, contacts, locations
- Quote acceptance service (per REQ-CRM-ACCEPT-01, Section 11.4)
- Client resolution flow (create new or select existing)
- SalesOrder + SalesOrderLine
- Sales Order state machine enforcement
- Quote version navigation in UI
- Quote expiry Celery beat task (idempotent)
- Tenant-facing UI: dashboard, leads, quotes, clients, orders

#### Exit criteria
- Lead → Quote → Acceptance → Client + SalesOrder completes end-to-end
- Accepted pricing snapshot is immutable after catalog edit
- Fulfillment generation stubs exist for all three line types (wired in Milestone 4)
- State machine invalid transitions are rejected

### Milestone 3 — Catalog and Pricing Engine
**Estimated duration:** 5–7 weeks

#### Scope
- Service, Product, RawMaterial, Supplier, SupplierProduct models
- BOM + BOMLine models with effective-from date versioning
- PricingContextBuilder, PricingEngine, strategy implementations (all three)
- Override and discount layer
- PricingSnapshotService
- PricingRule model and resolution (item-specific over line-type default)
- Catalog and BOM admin/UI
- Pricing engine unit tests with known inputs and expected outputs
- Snapshot replay test

#### Exit criteria
- All three line types can be priced using the strategy engine
- Snapshot replay produces identical outputs from stored inputs
- Authorized price override is logged; unauthorized attempt is rejected with 403
- Item-specific pricing rule overrides line-type default

### Milestone 4 — Operations Domain
**Estimated duration:** 8–12 weeks

#### Scope
- WorkOrder model and state machine (one per SalesOrderLine of service type)
- Work order assignment, status tracking, completion
- PurchaseOrder model and state machine
- PO creation from resale SalesOrderLines
- BuildOrder model and state machine
- BOM version snapshot at build start
- BuildLaborEntry model and entry UI
- Estimated vs actual cost tracking and variance calculation
- Fulfillment generation wiring (all three artifact types, idempotent)
- Order fulfillment check trigger (WO complete / Build approved → SalesOrder state check)
- Operations UI: work orders, purchase orders, build orders, cost analysis

#### Exit criteria
- Service lines generate WorkOrders; WorkOrders can be assigned and completed
- Accepted resale lines can generate Purchase Orders
- Accepted manufactured lines generate Build Orders with BOM snapshot
- Actual vs estimated cost report available per Build Order
- Duplicate artifacts not created on task retry
- State machine invalid transitions rejected for all three artifact types

### Milestone 5 — Billing and Async Completeness
**Estimated duration:** 4–6 weeks

#### Scope
- Invoice model and state machine
- Partial invoice support
- Payment model and recording
- Outstanding balance calculation
- Accounting integration boundary fields on Invoice and Payment
- Invoice and Quote PDF generation (async, django-storages)
- Email delivery tasks (all event types)
- Celery beat tasks: quote expiry, invoice overdue marking, invite expiry
- Failed task visibility in Django admin

#### Exit criteria
- Invoice created from SalesOrder, partially or fully
- Payment recorded; balance updates correctly
- Invoice PDF generated and accessible
- All email event types fire correctly with retry on failure
- Overdue invoices marked by Celery beat without duplicates

### Milestone 6 — Hardening and Release Preparation
**Estimated duration:** 4–6 weeks

#### Scope
- Cross-tenant leakage test suite
- RBAC capability coverage test (all URL patterns have required_capability or explicit exemption)
- Impersonation audit completeness test
- Pricing snapshot integrity test (replay produces identical output)
- State machine invalid transition tests
- Security hardening: CSRF, session config, CSP, HSTS
- Performance baseline: query count audits, N+1 detection
- Database index review
- Production Docker configuration (gunicorn, graceful shutdown)
- CI pipeline (lint → test → build → push)
- Staging environment bring-up
- Developer onboarding documentation

#### Exit criteria
- No cross-tenant leakage in automated tests
- CI pipeline green on merge
- Staging environment live and passing acceptance test suite
- New developer can run local environment in under 30 minutes following onboarding docs

---

## 30. Major Risks and Considerations

### 30.1 Tenant Leakage Risk
Row-based tenancy demands strict discipline. The biggest technical risk is accidental cross-tenant access through incorrectly scoped queries. The `TenantManager` enforcement test in CI is the primary mitigation.

### 30.2 Overusing Django Admin
If major workflows are pushed into admin instead of dedicated application screens, the platform will become harder to use and harder to secure cleanly.

### 30.3 Pricing Complexity Growth
Pricing rules often become much more complex over time. The strategy pattern architecture isolates each line type's logic, but rule resolution in the `PricingContextBuilder` must not become a complex conditional. New rules must be added as new `PricingRule` records, not as code branches.

### 30.4 Cross-Subdomain Auth Implementation Risk
The handoff token flow must handle: back-button replay (token already used), concurrent tabs, supplier-unreachable tenant subdomain, and logout behavior when both root-domain and tenant sessions exist. These cases must be specified in a technical design document before implementation.

### 30.5 Incomplete Inventory Assumptions
Because full inventory is deferred, the team must avoid accidentally building hidden inventory assumptions into purchasing or build logic.

### 30.6 Manufacturing Expansion Pressure
Build orders, BOMs, and actual costing can grow quickly into light ERP behavior. Phase boundaries must remain disciplined.

### 30.7 Idempotency Discipline
All Celery tasks that create state records (fulfillment artifacts, invoice generation, PDF generation) must be idempotent. This must be enforced by code review and tested explicitly.

---

## 31. Resolved Architecture Decisions

### 31.1 Confirmed Implementation Decisions

1. **Cross-subdomain auth:** Short-lived (60s), signed, single-use handoff token from root domain to tenant subdomain. Tenant-local session after handoff. Redis-backed token store for single-use enforcement.
2. **Background workers:** Celery + Redis. All state-altering tasks must be idempotent.
3. **Local subdomain development:** Reverse-proxy-based wildcard local domain (e.g. `*.mypipeline.local`).
4. **Document storage:** Local filesystem (dev/test); S3-compatible via `django-storages` (non-dev).
5. **Monitoring:** Structured JSON logging + Sentry (web and worker). OpenTelemetry optional later.
6. **Accounting integration:** No external product selected for v1. Internal integration boundary (external_id, sync_status, sync_error fields on Invoice and Payment).
7. **Advanced scheduling/dispatch:** Deferred. Basic assignment and scheduled dates only in v1.
8. **Quote versioning:** Parent Quote container + QuoteVersion children.
9. **Client matching on acceptance:** User explicitly selects or confirms client before acceptance transition completes.
10. **Pricing engine:** Strategy pattern by line type with shared override/discount layer. Engine invoked from service layer only.
11. **BOM versioning:** Effective-from date versioning. Build Orders reference specific BOM version at build start.
12. **Work order cardinality:** One SalesOrderLine generates exactly one WorkOrder.
13. **Concurrent tenant sessions:** One active tenant session per browser context. Sessions do not inherit across subdomains.
14. **Connection pooling:** pgBouncer in Docker environment from day one.
15. **Storage abstraction:** `django-storages` as the abstraction layer.

### 31.2 Deferred Selections (Not Current Blockers)
- Specific S3-compatible storage vendor
- Exact wildcard local development domain naming convention
- Log sink beyond Sentry
- External accounting package (if integration is later approved)
- Route optimization or richer scheduling tooling
- API layer beyond the internal integration boundary

---

## 32. Initial Acceptance Criteria by Area

### 32.1 Platform Foundation
- Custom email-first user model is active before first stable migration baseline
- A user may belong to multiple organizations
- A super-admin/support user may access multiple tenants
- Central login redirects to the correct tenant portal
- Tenant subdomain resolution works from organization slug
- Handoff token replay is rejected

### 32.2 RBAC
- All 73 capabilities seeded; all 9 default roles seeded
- Tenants can create additional roles
- Capabilities are enforced within organization context at view, queryset, and service layers
- Support impersonation cannot bypass audit requirements
- AuditEvents during impersonation carry both actor (support user) and on_behalf_of (target user)

### 32.3 State Machines
- All 8 entity state machines are enforced at the service layer
- Invalid transitions are rejected with a clear error
- Terminal states have no exits

### 32.4 CRM
- Lead can be created, updated, and converted to a quote
- Quote supports mixed line types
- Internal acceptance resolves client (create or link) and creates SalesOrder
- Accepted pricing snapshot remains unchanged after catalog edits
- One WorkOrder per service SalesOrderLine; one BuildOrder per manufactured SalesOrderLine

### 32.5 Pricing
- All three pricing strategies (Service, Resale, Manufactured) produce correct results from known inputs
- Pricing snapshot replay produces identical output
- Authorized price override is logged; unauthorized attempt is rejected
- Item-specific pricing rule overrides line-type default

### 32.6 Operations
- Service lines generate Work Orders; Work Orders can be assigned and completed
- Resale lines can generate Purchase Orders with supplier linkage
- Manufactured lines generate Build Orders with BOM version snapshot
- Build Orders support labor actual capture and actual vs estimated cost comparison
- Fulfillment generation tasks are idempotent

### 32.7 Billing
- Invoice can be created from order, partially or fully
- Payments can be recorded; balance updates correctly
- Invoice PDF can be generated asynchronously
- External reference ID fields, sync_status, and sync_error fields exist on Invoice and Payment

### 32.8 Audit / Support
- All state transitions produce AuditEvents
- Impersonation requires reason capture and produces ImpersonationAuditLog entry
- Pricing overrides are logged with original price, new price, actor, and reason
- Quote acceptance AuditEvent includes all generated artifact IDs
