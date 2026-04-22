# MyPipelineHero CRM
## Product Requirements & Architecture Specification

**Document status:** Revised Baseline  

**Prepared for:** MyPipelineHero CRM Development  

**Primary stack baseline:** Django 5.2 LTS, Python 3.14, PostgreSQL 17, Docker-first architecture  

**UI strategy:** Two-phase delivery
  - **Phase 1:** server-rendered Django templates for the full CRM build
  - **Phase 2:** custom React front-end for the tenant-facing application after the CRM is functionally complete.  

**Document Purpose:** Define the confirmed requirements, recommended system layout, phased roadmap, and implementation guardrails for a multi-tenant Django CRM that supports leads, quoting, clients, services, resale products, in-house manufactured products, purchasing, work execution, and invoicing — delivered first as a server-rendered Django application and subsequently reskinned with a React tenant portal over a stable service/API boundary.

---

## 1. Executive Summary

MyPipelineHero will be a **multi-tenant CRM and operations platform** built in **Django 5.2 LTS** with **Python 3.14**, **PostgreSQL 17**, and **Docker from the first commit forward**. The system will support both:

- **Services rendered** to clients, and
- **Products sold**, including:
  - purchased and resold items, and
  - custom products built in-house.

The core commercial workflow is:

**Lead → Quote → Acceptance → Client / Sales Order → Fulfillment Artifacts → Invoice**

Fulfillment artifacts must support:

- **Work Orders** for services,
- **Purchase Orders** for bought-and-resold items,
- **Build Orders** for in-house custom products.

The application will use **row-based multi-tenancy**, a **custom email-first user model**, **global support/super-admin users**, **organization-scoped membership and RBAC**, a **custom central login landing page** on the root domain, and **tenant subdomain portals** under the pattern:

`{slug}.mypipelinehero.com`

The Django admin will exist as the initial **internal platform/configuration console**, in Phase 1 while Tenant-facing workflows must live in the main CRM application UI in Phase 2.

The tenant-facing UI is delivered in two phases:

**Phase 1 (initial build):** 
- Server-rendered Django templates using the Django templating system. This phase delivers the complete CRM — all domains, workflows, state machines, pricing, fulfillment, and billing — behind Django views and templates. A **custom login landing page utilizing Bootstrap + custom css** served at the root domain allows both tenant users and platform/support users to authenticate. This is the primary product deliverable for the CRM build.

**Phase 2 (post-CRM):** 
- A custom **React** tenant-facing front-end replaces the tenant portal's Django-templated screens. The React application consumes a stable internal JSON API layer exposed by the Django backend. The Django admin, login landing page, and support/impersonation tooling remain server-rendered.

All Phase 1 implementation work must keep business logic in the service layer (not in views or templates) so the Phase 2 API layer can be built on top of the same services without duplication.

---

## 2. Confirmed Decisions

The following decisions were explicitly confirmed and must be treated as requirements, not suggestions.

### 2.1 Platform and Infrastructure
- Framework: **Django 5.2 LTS**
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
- Client model: **single client account with billing account details, contacts, and multiple locations/sites in v1**
- Client matching on acceptance: **user explicitly selects existing client or confirms new client creation before acceptance proceeds** 
- Acceptance: **internal status transition only** for initial implementation
- Billing: **include invoicing and payment tracking, but not full accounting**

### 2.5 UI / Admin Direction
- Application posture (Phase 1): **server-rendered Django using the Django templating system** for the complete CRM build
- Application posture (Phase 2, post-CRM): **custom React front-end** for the tenant-facing application, consuming an internal JSON API backed by the same Django service layer
- Admin direction: **Django admin for internal platform/configuration, not primary business workflows** — remains server-rendered in both phases
- Landing page requirement (Phase 1): **custom login landing page** on the root domain that authenticates both tenant users and platform/support users; full marketing site is deferred
- Tenant users are routed to `https://{slug}.mypipelinehero.com` in both phases
- Service-layer discipline is a UI-phase prerequisite: views and templates must remain thin so the Phase 2 API layer reuses existing services without logic duplication

### 2.6 Authorization
- RBAC model: **org-scoped roles + capability-level grants + support/super-admin exceptions**
- Platform must ship with **default roles/capabilities**
- Tenants may create **organization-scoped custom roles**
- Capabilities are **platform-defined system capabilities** in v1; tenants may assign them to roles and members but may not create custom capability codes
- Operating-scope restrictions by **Region / Market / Location** must be supported for scoped roles

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
  - **Sentry (or equivalent) required before first tenant production launch** for application and worker error monitoring
  - **OpenTelemetry optional later** if distributed tracing needs expand
- Accounting integration posture: **define an adapter/integration boundary now; defer product selection until later**
- Scheduling/dispatch posture: **basic work-order assignment/scheduling in the current phase; advanced dispatch/routing deferred**
- Internal API layer posture: **service-layer-first architecture in Phase 1**, with a thin internal JSON API to be introduced in Phase 2 to support the React tenant portal. No public/external API is in scope for v1. Views in Phase 1 may call a shared Django REST Framework (or equivalent) serializer/service pair where it is natural to do so, but the full API surface is not required until Phase 2.
- Front-end framework (Phase 2): **React**. The specific React toolchain (build tool, routing library, state/data-fetching library, component library) is deferred to a dedicated Phase 2 design sprint.

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
5. Provide a professional SaaS experience with a custom login landing page (Phase 1) and branded tenant portals.
6. Deliver the full CRM first as a server-rendered Django application (Phase 1), then reskin the tenant-facing portal with a React front-end (Phase 2) without rewriting business logic.
7. Support growth from a server-rendered monolith into a more modular platform over time.

### 3.2 Non-Goals for Initial Release
"Initial release" refers to Phase 1 (the server-rendered Django CRM, through Milestone 6). The following are intentionally out of scope for Phase 1 unless later approved:
- Full double-entry accounting / general ledger
- Full warehouse management system functionality
- Native e-signature platform implementation
- Native payment processor as system of record for accounting
- Mobile-native applications (Phase 2 React front-end is web-only; a native mobile app is not in scope)
- Customer-facing public quote builder (i.e. external, non-tenant users)
- Schema-per-tenant deployment model
- Public marketing website on the root domain (Phase 1 delivers only a custom login landing page; see Section 9.1)
- Public or third-party-facing API (the Phase 2 API is internal, consumed only by the first-party React tenant portal)
- Inbound email synchronization, mailbox threading, or full email-client behavior
- Shipment/delivery tracking as a dedicated operational domain
- Ad hoc report builders or saved custom-report designers

---

## 4. Guiding Principles

1. **Tenant safety over convenience** — no cross-tenant leakage.
2. **Commercial history is immutable enough to audit** — sent quotes, accepted pricing, generated orders, and posted payments must be reproducible without destructive in-place edits.
3. **Workflow objects must reflect operational reality** — quote acceptance alone is not fulfillment.
4. **The admin is not the application** — use admin for back-office/platform tasks; use application screens for operational workflows.
5. **A custom user model is required from day one** — no retrofit later.
6. **Docker is first-class, not an afterthought** — dev, CI, and production workflows must respect this.
7. **Design for role flexibility** — default roles are required, but tenant-specific extensions must be supported.
8. **Build for observability and auditability** — especially impersonation, tenant switching, pricing overrides, and status transitions.
9. **The service layer is the stable contract** — Phase 1 delivers the CRM through Django views and templates, but every state-changing operation lives in a service function with a plain-Python signature. Phase 2's React + API migration is a UI swap, not a domain rewrite. Views are thin; templates contain no business logic; state machines are enforced in services; pricing runs through the engine from services only.

---

## 5. High-Level Architecture

### 5.1 Architectural Style
The platform is delivered in two UI phases against a single shared backend.

**Phase 1 — server-rendered Django.** The entire CRM is implemented as a conventional Django application using Django views, forms, templates (the Django templating system), and a service-layer orchestration pattern. This is the primary build effort.

**Phase 2 — React tenant portal.** After the Phase 1 CRM is functionally complete, a custom React front-end replaces the tenant-portal screens. React consumes a thin internal JSON API exposed by the Django backend. The Django admin, the login landing page, and all support/impersonation tooling remain server-rendered.

The implementation, in both phases, must:
- prioritize Django-native patterns for the backend,
- keep business logic out of templates and thin views,
- centralize domain workflows in service/application layers so both Django views and the Phase 2 API can call the same services,
- treat the service layer as the stable contract — UI technology changes must not require rewriting domain logic,
- allow the Phase 2 API to be grown incrementally on top of existing services without forcing API-first architecture onto v1.

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
- CRM Pipeline / Tasks / Communications
- Catalog / Pricing
- Manufacturing / Procurement / Work Execution / Operating Locations
- Billing / Invoicing
- Reporting / Audit / Support / Analytics
- Files / Document Attachments

### 5.4 Application Service Boundary
The application service layer is the authoritative orchestration boundary for all state-changing operations.

#### Requirements
- Every state-changing workflow must execute through an application/service-layer function with plain-Python inputs and outputs.
- Services must own transaction boundaries, domain validation, authorization hooks, audit-event emission, and async-side-effect publication.
- Services must raise typed domain exceptions; they must not return HTTP responses or depend on Django request objects.
- Django views, forms, admin actions, Celery tasks, and Phase 2 API endpoints must call the same services rather than implementing parallel workflow logic.
- Models may enforce local invariants but must not orchestrate multi-object workflows or cross-domain side effects in `save()` methods or signals.

### 5.5 Async and Outbox Boundary
Async processing is required, but state mutation and side-effect dispatch must remain reliable under retries and failures.

#### Requirements
- State-changing services that trigger async side effects must persist those side effects through a transactional outbox or equivalent durable publication mechanism before worker pickup.
- Quote acceptance, invoice send, reminder/notification dispatch, outbound email delivery, and report export are required outbox candidates.
- Celery workers must consume idempotent work items and must be safe to retry without duplicating business artifacts.
- Background tasks may execute automated transitions, but the transition rules remain owned by the same domain services used by synchronous application flows.

### 5.6 Domain Boundaries and Linkage Rules
The platform must avoid convenience patterns that weaken integrity in a multi-tenant operational system.

#### Requirements
- Tasks and communications must not use Django `GenericForeignKey` or equivalent generic polymorphic relations for their primary business-object linkage.
- Cross-domain links for tasks and communications must be implemented using typed link tables or explicit foreign keys with database constraints.
- Tenant-owned document attachments must be modeled as a first-class domain and access-controlled through the same tenancy and RBAC rules as their parent records.
- Scope-sensitive operational records should persist a resolved `location` reference where practical rather than relying only on multi-hop derived scope.

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
| Draft | Sent | send_quote | Sales rep | Email notification queued (async); sent version becomes immutable |
| Draft | Superseded | new_version_created | Quote editor | New version created in DRAFT; this version locked |
| Sent | Retracted | retract_quote | Sales rep | Sent version locked; successor QuoteVersion created in DRAFT |
| Sent | Accepted | accept_quote | Authorized (quotes.approve) | SalesOrder created; pricing snapshot frozen; fulfillment artifacts dispatched async |
| Sent | Declined | decline_quote | Authorized user | — |
| Sent | Expired | expiry_check | System — Celery beat, daily | expiration_date has passed |
| Sent | Superseded | new_version_created | Quote editor | New version created in DRAFT; sent version remains preserved for audit |

**Terminal states:** Accepted, Declined, Expired, Retracted, Superseded — no transitions out.

### 6.3 Sales Order

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Open | Cancelled | cancel_order | Manager (orders.cancel) | Only if no active WO/PO/BuildOrder; reason required |
| Open | In fulfillment | fulfillment_started | System | First fulfillment artifact leaves initial state |
| In fulfillment | Fulfilled | all_fulfillment_complete | System | All WOs/POs/BuildOrders in terminal state |
| In fulfillment | Part. invoiced | partial_invoice_issued | Billing user | Invoice created for subset of currently invoiceable order lines |
| Fulfilled | Part. invoiced | partial_invoice_issued | Billing user | Invoice created for subset of currently invoiceable order lines |
| Fulfilled | Invoiced | full_invoice_issued | Billing user | All currently invoiceable lines have been invoiced |
| Part. invoiced | Invoiced | remaining_invoiced | Billing user | All currently invoiceable lines have now been invoiced |
| Invoiced | Closed | payment_complete | System | All invoiceable lines have been fully invoiced and fully paid; no uninvoiced eligible lines remain |

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

### 6.8 Task

| From | To | Trigger Event | Actor | Side Effects / Notes |
|---|---|---|---|---|
| Open | In progress | start_task | Assigned user / Manager | — |
| Open | Blocked | block_task | Assigned user / Manager | Reason required |
| In progress | Blocked | block_task | Assigned user / Manager | Reason required |
| Blocked | In progress | resume_task | Assigned user / Manager | — |
| Open | Completed | complete_task | Assigned user / Manager | Completion notes optional |
| In progress | Completed | complete_task | Assigned user / Manager | Completion notes optional |
| Open | Cancelled | cancel_task | Manager | Reason required |
| In progress | Cancelled | cancel_task | Manager | Reason required |
| Blocked | Cancelled | cancel_task | Manager | Reason required |
| Completed | Open | reopen_task | Manager / `tasks.manage` | Reason required |
| Cancelled | Open | reopen_task | Manager / `tasks.manage` | Reason required |

**Terminal states:** None — reopening is permitted only through explicit reopen transitions with audit logging.

### 6.9 Membership

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

### 7.2A Operating Scope Model
The platform must support organization-internal operating scopes for geographically or operationally segmented access.

#### Required operating-scope entities
- **Region** — top-level operating scope within an organization
- **Market** — child scope under a Region
- **Location** — child scope under a Market

#### Requirements
- Region, Market, and Location are organization-scoped records.
- A Market must belong to exactly one Region.
- A Location must belong to exactly one Market.
- Tenant-owned records that participate in scoped access must be able to reference a Location directly or resolve to a Location through related data.
- Regional Manager, Market Manager, and Location Manager roles must be enforced using explicit operating-scope assignments, not naming convention alone.
- Memberships must support one or more scope assignments at the Region, Market, or Location level.
- Scoped-role querysets must be restricted to records that fall within the membership's assigned operating scopes.
- Object-level authorization must deny access when the target record falls outside the acting membership's permitted Region/Market/Location scope, even if the user otherwise holds the required capability.

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
The root domain `mypipelinehero.com` must provide different experiences in each UI phase.

#### Phase 1 — Custom Login Landing Page
During the Django-first CRM build, the root domain must provide a **custom login landing page** serving as the single authentication entry point for the platform. A full public marketing site is **not** required in Phase 1.

Phase 1 root site requirements:
- custom branded login landing page (server-rendered Django templates)
- login entry point for **tenant users** (members of one or more organizations)
- login entry point for **platform/support users** (super-admins and support staff), using the same login form — user type is determined by identity, not by a separate URL
- password reset flow
- invite acceptance flow
- organization picker for multi-org users after authentication
- post-login routing to the appropriate tenant subdomain (tenant users) or the platform console (platform users)
- lightweight public pages only as needed (e.g., terms, privacy, support contact); no marketing funnel

#### Phase 2 — Public Marketing Site (future)
In Phase 2 or later, the root domain may be expanded to host a full public marketing site (product messaging, demo request, pricing, etc.) alongside the login landing page. The Phase 1 login landing page must be designed so it can be embedded in, or coexist with, a future marketing site without rework to the authentication flow.

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
- Tenant logout must terminate only the tenant-local session for the current subdomain and must not implicitly end the authenticated root-domain session.
- Root-domain logout must terminate the root-domain session and invalidate tenant-session renewal/handoff paths; this behavior must be documented and covered by automated tests.
- A shared parent-domain cookie strategy must **not** be used as the primary tenant-session mechanism.

### 9.5 Session Behavior Across Tenants
- A user may have one active tenant session per browser context at a time.
- Opening a second tenant subdomain in the same browser does not invalidate the first session but does not inherit context from it.
- Support impersonation sessions are distinct from the impersonating user's own tenant session.

---

## 10. Authorization and RBAC Requirements

### 10.1 Authorization Model
The platform must support **org-scoped RBAC with capability-level grants** and optional **Region / Market / Location** operating-scope restrictions for scoped roles.

### 10.2 Evaluation Algorithm
Permission checks must execute the following steps in order. No step may be skipped.

1. If `user.is_superuser` → grant (short-circuit)
2. If an active impersonation session is present → evaluate capabilities as the impersonated membership; record all actions under the original support user identity
3. Retrieve the user's active Membership for the current organization; if none → deny
4. Collect all capabilities from the membership's assigned Roles via RoleCapability
5. Apply MembershipCapabilityGrant overrides: GRANT overrides add capabilities; DENY overrides remove capabilities and take precedence over role grants
6. If the required capability is in the final set → grant; otherwise → deny
7. For object-level checks: additionally verify the target object belongs to the active organization and that any status-based restrictions are satisfied
8. If the acting membership is subject to Region / Market / Location operating-scope restrictions, verify the target object falls within that permitted scope; otherwise deny

### 10.3 Capability Registry
The following system-defined capabilities are shipped as seed data via a data migration. Capability codes follow the pattern `{domain}.{resource}.{action}`.

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
| `quotes.retract` | Retract a sent quote | Status check: SENT only; original sent version remains immutable and a successor draft is created |
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
| `billing.payment.edit` | Record a payment correction / adjustment workflow | Must not mutate posted payment history in place |
| `billing.reports.view` | View billing reports and balance summaries | |

#### Task Management (`tasks.*`)

| Code | Name | Notes |
|---|---|---|
| `tasks.view` | View tasks | |
| `tasks.create` | Create tasks | |
| `tasks.edit` | Edit tasks | Must be creator, assignee, or manager unless `tasks.manage` |
| `tasks.assign` | Assign or reassign tasks | |
| `tasks.complete` | Mark task completed | |
| `tasks.manage` | Full task management | Includes cancel / reopen / override; reopen requires reason and audit event |

#### Communications (`communications.*`)

| Code | Name | Notes |
|---|---|---|
| `communications.view` | View communication history | |
| `communications.log` | Log inbound or outbound communication | |
| `communications.send` | Send supported outbound communication | Delivery may be async |
| `communications.manage` | Edit/redact communication metadata where allowed | Original message body remains immutable once sent |

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
| Regional Manager | Regional level managers | All except platform-level actions; restricted to their assigned Region scope |
| Market Manager | Market level managers | All except platform-level actions; restricted to their assigned Market scope |
| Location Manager | Location level managers | All except platform-level actions; restricted to their assigned Location scope |
| Sales Staff | Salespeople | `leads.*`, `quotes.view/create/edit/send`, `clients.view/create/edit`, `tasks.view/create/edit`, `communications.view/log`, `orders.view`, `catalog.view` |
| Service Staff | Field service worker | `workorders.view`, `workorders.update_status`, `workorders.complete`, `tasks.view`, `tasks.complete` — own WOs/tasks only unless elevated |
| Production Staff | Shop floor | `build.view`, `build.manage`, `build.labor.record`, `tasks.view`, `tasks.complete` — own build orders/tasks only unless elevated |
| Viewer | Read-only stakeholder | `*.view` capabilities only, no mutations |

**Customization rule:** Tenants may create new roles and assign any system-defined capabilities to them. They may not create custom capability codes in v1. They may not modify the seeded default roles (those are read-only templates). Tenants may modify role assignments for their own members freely via the org admin UI.

**Scoped-role rule:** Regional Manager, Market Manager, and Location Manager assignments are valid only when the membership has corresponding explicit operating-scope assignments. A scoped role without scope assignment grants no data access outside organization-wide non-data actions.

### 10.5 RBAC Enforcement Matrix
The following matrix maps every view and action to its queryset scope, required capability, object-level check, and audit event. Every row is an enforced requirement.

**Three-layer rule:** Queryset scoping, view-level capability check, and object-level state/ownership check are all required. No layer substitutes for another.

**Scoped-access rule:** For memberships restricted by Region / Market / Location, queryset scope must also be intersected with the membership's permitted operating scope.

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
| Retract quote | `for_org(org)` | `quotes.retract` | `version.status == SENT`; original sent version remains immutable and a successor draft is created | `QUOTE_RETRACTED` |
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
| Record payment correction | `for_org(org)` | `billing.payment.edit` | creates reversal/adjustment linked to original payment; original payment remains immutable | `PAYMENT_ADJUSTED` |

#### Task Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Task list | `for_org(org)` filtered by assignee/creator unless elevated | `tasks.view` | — | — |
| Task detail | `for_org(org)` | `tasks.view` | must be creator, assignee, or manager unless `tasks.manage` | — |
| Create task | `for_org(org)` | `tasks.create` | linked objects must belong to org | `TASK_CREATED` |
| Edit task | `for_org(org)` | `tasks.edit` | must be creator, assignee, or manager unless `tasks.manage` | `TASK_UPDATED` |
| Assign task | `for_org(org)` | `tasks.assign` | assignee membership belongs to org | `TASK_ASSIGNED` |
| Complete task | `for_org(org)` | `tasks.complete` | task status in {OPEN, IN_PROGRESS, BLOCKED} | `TASK_COMPLETED` |
| Cancel task | `for_org(org)` | `tasks.manage` | task status not COMPLETED/CANCELLED; reason required | `TASK_CANCELLED` |
| Reopen task | `for_org(org)` | `tasks.manage` | task status in {COMPLETED, CANCELLED}; reason required | `TASK_REOPENED` |

#### Communication Domain

| View / Action | Queryset Scope | View Capability | Object Check | Audit Event |
|---|---|---|---|---|
| Communication list | `for_org(org)` | `communications.view` | — | — |
| Communication detail | `for_org(org)` | `communications.view` | linked object belongs to org | — |
| Log communication | `for_org(org)` | `communications.log` | linked object belongs to org | `COMMUNICATION_LOGGED` |
| Send communication | `for_org(org)` | `communications.send` | recipient/linked object belongs to org and delivery channel is enabled | `COMMUNICATION_SENT` |
| Edit communication metadata | `for_org(org)` | `communications.manage` | original sent body immutable; metadata edits only | `COMMUNICATION_UPDATED` |

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

#### Quote container model (resolved — LF-02)
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
- Sent quote versions are immutable; retraction creates a successor DRAFT version rather than re-opening the same sent version
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
   - SalesOrderLines with `line_type = RESALE_PRODUCT` are flagged for Purchase Order generation; PO creation may be completed in the purchasing workflow using explicit allocation records between SalesOrderLine and one or more PurchaseOrderLine records.
   - SalesOrderLines with `line_type = MANUFACTURED_PRODUCT` each trigger creation of exactly one BuildOrder in status PLANNED, recording the currently planned BOM version reference. At `start_build`, the system must create an immutable BOM snapshot used for execution and costing.
5. **Fulfillment-line granularity simplification (v1):** The one-WorkOrder-per-service-line and one-BuildOrder-per-manufactured-line rules are intentional v1 simplifications. Quote and order lines must therefore represent a single fulfillable unit. If an item requires multiple independently tracked visits, batches, or fulfillment steps, it must be split into multiple quote/order lines before acceptance.
6. **Idempotency:** Fulfillment generation tasks must be idempotent. Each SalesOrderLine may have at most one WorkOrder and at most one BuildOrder. Resale-product fulfillment must support one-to-many and many-to-many allocation between SalesOrderLine and PurchaseOrderLine records.
7. **Audit event:** `QUOTE_ACCEPTED` is recorded with actor, QuoteVersion reference, Client reference, SalesOrder ID, and IDs of all generated fulfillment artifacts.

### 11.5 Client Requirements
Clients are long-lived customer entities, not merely converted leads.

#### v1 client-account posture
v1 does **not** implement parent/child customer hierarchy. The client model represents a single tenant-scoped client account with billing-account details, contacts, and multiple locations. Hierarchical account structures may be considered in a future phase, but v1 must not imply or partially implement them.

#### Required support
- billing account details on the client record
- multiple contacts
- multiple service/delivery/install locations
- history of orders, quotes, invoices, and communications
- active/inactive status
- tenant-scoped uniqueness and searchability

### 11.6 Task Requirements
Tasks are required in Phase 1 and must be first-class tenant-facing workflow objects, not informal notes.

#### Required support
- create, assign, reassign, update, complete, block, cancel, and reopen tasks
- link tasks to leads, quotes, clients, sales orders, work orders, build orders, purchase orders, invoices, or organization-level operations using typed link tables or explicit foreign keys; generic polymorphic relations are prohibited
- support due date, priority, assignee, creator, status, notes, and completion metadata
- support list views for "my tasks", team tasks, and object-linked tasks
- enforce tenant and operating-scope restrictions
- emit audit events for create, assign, status change, cancel, and reopen actions
- support async reminders/notifications for upcoming or overdue tasks

### 11.7 Communications Requirements
Communications are required in Phase 1 and must provide auditable customer-interaction history.

#### v1 communications boundary
v1 communications support is intentionally limited to:
- outbound email, and
- manual call/note logging.

Inbound email synchronization, mailbox threading, and full email-client behavior are out of scope for v1.

#### Required support
- log outbound email and manual call/note communications against leads, clients, quotes, sales orders, work orders, build orders, purchase orders, and invoices
- store direction, channel, subject/summary, body or note, participants, timestamp, actor, and typed communication links; generic polymorphic relations are prohibited
- preserve immutable history for sent outbound email; later metadata edits must not rewrite the original sent body
- store outbound-provider metadata where applicable, including provider message ID and delivery status fields
- support communication timeline views on related business records
- support async delivery for outbound email and async status capture where applicable

### 11.7A Document and Attachment Requirements
Document handling is required in v1 as a first-class domain, not as ad hoc file fields scattered across business models.

#### Required support
- quote PDFs, invoice PDFs, uploaded files, and completion photos must use a shared document-attachment abstraction
- each attachment must be organization-scoped and linked to a supported business record through explicit, permission-aware linkage
- binary file content must live in the configured storage backend; the database stores metadata and storage references only
- attachment access must enforce tenant, capability, and object-level authorization
- attachments must capture uploader, filename, content type, size, storage key, and timestamps
- malware scanning and retention/cleanup hooks must be supported by the storage workflow even if scanner implementation is introduced later

### 11.8 Sales Order Requirements
The Sales Order is the operational anchor after acceptance.

#### Required functions
- represent the accepted commercial commitment
- hold order-level status (see state machine, Section 6.3)
- group mixed line types
- drive fulfillment generation
- support invoicing linkage
- support order-level notes and audit history
- preserve accepted commercial terms

#### Order closure rule
A SalesOrder may transition to `CLOSED` only when all invoiceable lines under the organization's active billing policy have been fully invoiced and fully paid and no uninvoiced eligible lines remain.

### 11.9 Change and Revision Considerations
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
- procurement must support explicit allocation between one SalesOrderLine and one or more PurchaseOrderLine records
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
- resale-product fulfillment must support split procurement across multiple purchase orders when needed
- generation tasks must be idempotent

---

## 13. Pricing and Costing Requirements

### 13.1 Pricing Engine Architecture (resolved — LF-05)
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
| Manufactured product | SUM(BOM material costs + estimated labor cost) | Markup % over total estimated cost | Multi-component BOM plus labor estimate |

#### Confirmed formula for manufactured products
```
Sales Price = [(SUM(cost of materials) + estimated labor cost) × (1 + markup %)] - discounts
```

Manufactured product quoted pricing in v1 includes estimated material cost and estimated labor cost, each captured in the pricing snapshot.

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

Catalog or cost changes after acceptance must not silently rewrite historical commercial records. PricingSnapshot records are written once and never updated; superseded snapshots from re-pricing are retained with `is_active = False`. Pricing snapshots for manufactured products must capture estimated material cost, estimated labor cost, markup inputs, discounts, and final effective price.

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
Full inventory management is not required in the current phase. The data model should avoid blocking future inventory expansion. Shipment/delivery tracking is also deferred in v1 and must not be implied by invoiceability rules unless a dedicated domain is later approved.

---

## 15. Manufacturing / Build Requirements

### 15.1 Build Orders
Build Orders are required for custom/in-house product development.

#### Required features
- create Build Orders from accepted order lines (one per SalesOrderLine of manufactured type)
- support status lifecycle (see state machine, Section 6.6)
- record the planned BOM version reference at creation time; create an immutable BOM snapshot at build start
- track estimated material/labor
- track actual material/labor
- record completion state
- link finished build output back to source order lines

### 15.2 BOM Requirements
The platform must support BOM definitions for manufactured products with version history.

#### BOM versioning strategy (resolved — LF-06)
- BOMs use effective-from date versioning.
- Each BOM version is immutable once active.
- Build Orders record the currently planned BOM version reference at creation time for planning visibility.
- The immutable execution BOM snapshot is taken at `start_build` (when the Build Order transitions from PLANNED to IN PROGRESS), not at quote time.
- Historical costing, variance analysis, and execution audit must reference the immutable build snapshot rather than a mutable product-to-BOM relationship.
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
- correct posted payments only through explicit reversal/adjustment workflows, never by silent in-place mutation

### 17.3 Invoice Eligibility Rules
Invoice creation must enforce explicit invoiceability rules by line type.

#### Required posture
- Service lines become invoiceable upon WorkOrder completion unless overridden by organization billing policy.
- Resale-product lines become invoiceable upon receipt or manual release per organization billing policy.
- Manufactured-product lines become invoiceable upon BuildOrder completion or manual release per organization billing policy.
- The chosen invoiceability behavior must be configuration-backed and auditable, not ad hoc per-user behavior.
- Invoice creation services must reject lines that are not yet invoiceable under the active organization policy.

### 17.4 Financial Processing Baseline
v1 financial processing must support a deterministic baseline even though full accounting is out of scope.

#### Required baseline
- single base currency per organization
- `currency_code` stored on financial records from v1
- decimal monetary storage with deterministic rounding rules
- line-level taxable flags and invoice/order tax calculation
- support for payment allocation to one or more invoices
- support for overpayment prevention or explicit overpayment handling rules
- support for partial payments and balance recalculation
- deterministic invoice total, tax, and balance replay from stored line data

#### Explicitly out of scope for v1 unless later approved
- credit notes
- refunds
- write-offs
- multi-currency invoicing within a single organization

#### Payment correction policy
Recorded payments are append-only. Posted payment amounts and allocations must not be edited in place. Corrections must be handled through reversal or adjustment records linked to the original payment, with full audit attribution.

### 17.5 Accounting Boundary
The billing domain must remain internally functional for invoicing and payment tracking.

#### Required posture
- The implementation must define a stable adapter/integration boundary so future accounting sync does not require major domain rewrites.
- Client, invoice, and payment models must support external reference IDs, sync status fields, and sync error metadata.
- No external accounting product is selected for v1; selection is intentionally deferred.

### 17.6 Reporting Scope Boundary
Reporting is in scope only as a constrained operational feature set in v1.

#### Required posture
- v1 reporting is limited to fixed operational reports and CSV exports.
- Saved custom report builders, ad hoc metric designers, and generic analytics tooling are out of scope for v1 unless separately approved.
- Report exports must respect tenant scoping, capability checks, and audit logging.
- Long-running report generation must execute asynchronously.

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
- Users, Organizations, Memberships, Membership Scope Assignments, Roles, Capabilities, Audit Events, Impersonation Log

**CRM**
- Leads, Quotes, Clients, Tasks, Communications, Sales Orders, Invoices

**Catalog**
- Services, Products, Raw Materials, BOMs, Suppliers, Pricing Rules

**Operations**
- Regions, Markets, Locations, Purchase Orders, Build Orders, Work Orders

**Reporting**
- Fixed reports, report export jobs, snapshots / exports 

### 18.4 Admin Ordering Requirement
Custom app ordering and model ordering must be supported and not left to Django's default alphabetical ordering.

---

## 19. Main Application UI Requirements

The tenant-facing application UI is delivered in two phases. Phase 1 is a server-rendered Django application that delivers the complete CRM. Phase 2 replaces the tenant-facing portion with a custom React front-end once the CRM is functionally complete.

### 19.1 Application Experience (both phases)
The tenant portal must provide business-facing screens for at least:
- dashboard/home
- leads
- quotes
- clients
- tasks
- communications
- orders
- work orders
- purchase orders
- build orders
- invoices
- tenant administration (members, roles, org settings)
- fixed reports / exports

Tasks and communications are required Phase 1 domains, not placeholder navigation items. They must be implemented with the minimum capabilities defined in Sections 11.6 and 11.7.

Phase 2 must deliver feature parity with Phase 1 across all of the above before Phase 1 tenant screens may be retired.

### 19.2 Phase 1 — Server-Rendered Django Templating
All tenant-facing screens in Phase 1 must be implemented using the **Django templating system** with conventional Django views and forms.

#### Requirements
- Implement using Django views, Django forms, and Django templates — no standalone SPA framework in Phase 1.
- Template inheritance from a shared base layout; reusable includes/partials for common components (tables, filters, form fields, status badges, pagination).
- Progressive enhancement only (small, scoped JavaScript for interactive behaviors such as inline validation, modal dialogs, or pricing previews). A full client-side state framework is out of scope for Phase 1.
- HTMX or similar server-driven interactivity is permitted where it meaningfully improves UX (e.g., dynamic line-item editing on a quote) but is not mandated; decisions made case-by-case.
- CSRF tokens, standard Django form rendering, and Django messages framework for user feedback.
- Server-rendered pagination, filtering, sorting, and search — no client-side data grids.
- All views must be thin: they must delegate every state-changing operation to the service layer. Views must not embed business logic. This is enforced by code review and is a prerequisite for Phase 2.

#### Explicit scope
- Phase 1 is the CRM. Every domain, workflow, and state machine listed elsewhere in this document is implemented here.
- Phase 1 ships to production and is used by real tenants until Phase 2 replaces the tenant-facing screens.

### 19.3 Phase 2 — Custom React Tenant-Facing Front-End
Once the Phase 1 CRM is functionally complete and stable in production, a custom React front-end replaces the tenant-facing screens.

#### Requirements
- Implemented in **React** as a single-page application served from the tenant subdomain (`https://{slug}.mypipelinehero.com`).
- Consumes a thin internal JSON API exposed by the Django backend (see Section 19.5).
- Authenticates using the existing handoff token flow (Section 9.4); after handoff, the tenant-local session authorizes API calls (cookie-based or equivalent — specific mechanism selected in the Phase 2 design sprint).
- Must enforce the same RBAC capability model as Phase 1. The API, not the React client, is the authoritative enforcement point; the client uses capability data to show/hide UI but never as a security boundary.
- Must respect the same organization context model — API requests are always scoped to the active organization.
- Must deliver feature parity across all screens listed in Section 19.1 before Phase 1 tenant screens are retired.

#### Explicit out-of-scope for Phase 2 initial release
- Native mobile applications
- Offline-first behavior
- Customer-facing (external, non-tenant) UI

#### Deferred Phase 2 selections
The following are intentionally deferred to a dedicated Phase 2 design sprint and are not required to be resolved before Phase 1 begins:
- React build tool / framework (e.g., Vite + React, Next.js in SPA mode, Remix, etc.)
- Routing library
- Data-fetching / caching library (e.g., TanStack Query, RTK Query)
- Component / design system library
- CSS strategy (CSS-in-JS vs utility-first vs CSS modules)
- Build/deployment pipeline for the React bundle (served by Django vs separate static host vs CDN)

### 19.4 Components Retained Server-Rendered in Phase 2
The following components remain server-rendered Django templates in Phase 2 and are **not** migrated to React:
- Django admin / internal platform console (Section 18)
- Custom login landing page on the root domain (Section 9.1)
- Password reset, invite acceptance, and organization picker flows
- Support impersonation tooling and banner
- Email templates (invoice PDFs, notification emails, etc.)
- Error pages, terms/privacy pages, health check pages

The cross-subdomain handoff flow (Section 9.4) is unchanged between phases.

### 19.5 Internal API Layer (Phase 2 prerequisite)
A thin internal JSON API must be introduced to support the Phase 2 React client.

#### Required posture
- The API is **internal**, not public. It is consumed only by the first-party React tenant portal. A public/external API is out of scope for Phase 2 initial release.
- The API must be a thin layer over the existing service layer. It must not re-implement business logic or bypass service-layer orchestration.
- Every API endpoint must enforce the same three-layer RBAC rule as Phase 1 (queryset scoping + capability check + object-level check, per Section 10.5).
- Every state-changing API endpoint must produce the same AuditEvent as its Phase 1 view counterpart.
- Pricing must be executed by the same `PricingEngine` strategies invoked from the same service layer; the API must not introduce an alternate pricing path.
- State machine transitions must go through the same service methods; direct API mutations of status fields are prohibited.
- The API library selection (e.g., Django REST Framework, Django Ninja) is deferred to the Phase 2 design sprint. Tenants and capabilities are not affected by this choice.

#### Phase 1 obligations to support Phase 2 API
- Service layer must be exhaustive — every state-changing operation invoked by a Phase 1 view must have a corresponding service function.
- Services must accept plain Python arguments (not Django request objects) and return plain Python results, so they are directly callable from API views.
- Domain errors must be raised as typed exceptions (not HTTP responses) so the API layer can translate them consistently.

### 19.6 Scheduling and Dispatch Boundary
For both Phase 1 and Phase 2 initial delivery, tenant-facing work-order UX must support basic assignment, due/scheduled dates, checklists, notes, and completion tracking. Advanced dispatch capabilities are explicitly deferred.

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
- task reminder and overdue notifications
- outbound communication delivery and delivery-status capture where applicable
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
- State-changing services that enqueue async side effects must persist those side effects through a transactional outbox or equivalent durable publication mechanism
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

**Organization:** name, slug, status, primary contact information, timezone, base_currency_code, tax_settings / billing_policy configuration, timestamps

**Membership:** user, organization, status, role assignments, first name, last name, phone number, default flags, timestamps

**MembershipScopeAssignment:** membership, scope_type (REGION/MARKET/LOCATION), region/market/location reference, timestamps

**Role:** organization (nullable for system roles), code, name, description, timestamps

**Capability:** code, name, category/group, description, timestamps

**RoleCapability:** role, capability

**MembershipCapabilityGrant:** membership, capability, grant_type (GRANT/DENY)

**ImpersonationAuditLog:** acting support user, target membership or user, organization, reason, session_id, start/end timestamps, metadata

**AuditEvent:** organization (nullable), actor, on_behalf_of (nullable — for impersonation), event_type, object reference metadata, request_id, tenant_host, source_ip, masked before/after data, timestamps

### 22.2 CRM

**Lead:** organization, region/market/location (nullable as required for scoped access), lead number/code, source, status, owner, summary fields, timestamps

**LeadContact:** lead, name, email, phone, role/title

**LeadLocation:** lead, address fields, location notes

**Quote:** organization, lead (nullable), client (nullable), quote_number, timestamps

**QuoteVersion:** quote (FK), version_number, status, expiration_date, subtotal, discount, total, timestamps

**QuoteVersionLine:** quote_version, line_type, catalog references (nullable by type), description snapshot, quantity, unit price snapshot, discount, total, pricing_snapshot (FK)

**PricingSnapshot:** organization, quote_line (nullable), line_type, is_active, engine_version, inputs (JSON), outputs (JSON), effective_unit_price, effective_line_total, override_applied, created_at, created_by

**Client:** organization, region/market/location (nullable as required for scoped access), client_number, billing_account_name, status, notes, external_id (for accounting integration), timestamps

**ClientContact:** client, contact details, role/title, flags

**ClientLocation:** client, location name, address fields, type flags (billing/service/install)

**Task:** organization, title, description, status, priority, due_at, created_by, assigned_to, completed_at, completed_by, timestamps

**TaskLink:** task, lead (nullable), quote (nullable), client (nullable), sales_order (nullable), work_order (nullable), build_order (nullable), purchase_order (nullable), invoice (nullable), organization_operation_label (nullable), constraint that exactly one target is populated

**Communication:** organization, direction, channel, subject, body_or_note, participants, occurred_at, sent_at, created_by, delivery_status, provider_message_id, immutable_body_hash (where applicable), timestamps

**CommunicationLink:** communication, lead (nullable), quote (nullable), client (nullable), sales_order (nullable), work_order (nullable), build_order (nullable), purchase_order (nullable), invoice (nullable), constraint that exactly one target is populated

**DocumentAttachment:** organization, linked object metadata via typed attachment links or explicit foreign keys, storage_key, original_filename, content_type, size_bytes, uploaded_by, visibility_policy, malware_scan_status, timestamps

**SalesOrder:** organization, region/market/location (nullable as required for scoped access), client, originating quote version, order_number, status, totals snapshot, external_id, timestamps

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

**Region:** organization, code, name, active flag, timestamps

**Market:** organization, region, code, name, active flag, timestamps

**Location:** organization, market, code, name, address fields, active flag, timestamps

**PurchaseOrder:** organization, region/market/location (nullable as required for scoped access), supplier, order_number, status, source sales order references, totals, external_id, timestamps

**PurchaseOrderLine:** purchase order, product reference, description snapshot, quantity ordered, quantity received, unit cost

**PurchaseAllocation:** organization, sales_order_line, purchase_order_line, allocated_quantity, timestamps

**BuildOrder:** organization, region/market/location (nullable as required for scoped access), source sales order line, planned_bom_version, status, estimated material cost, actual material cost, estimated labor cost, actual labor cost, timestamps

**BuildBOMSnapshot:** build_order, source_bom_version, snapshot_payload, captured_at, captured_by

**BuildLaborEntry:** build order, user, hours/duration, applied rate/cost, notes, timestamps

**WorkOrder:** organization, region/market/location (nullable as required for scoped access), source sales order line, client, client location, status, assigned user, scheduled date, completed date, outcome notes

### 22.5 Billing

**Invoice:** organization, client, sales order, invoice_number, status, currency_code, subtotal_amount, tax_amount, total_amount, amount_paid, balance_due, due_date, external_id, sync_status, sync_error, timestamps

**InvoiceLine:** invoice, source order line reference, description snapshot, quantity, unit price, line_subtotal, taxable_flag, tax_amount, total

**Payment:** organization, client, amount, payment_date, method, reference, external_id, notes, unapplied_amount, timestamps

**PaymentAllocation:** payment, invoice, amount_applied, timestamps

**PaymentAdjustment / PaymentReversal:** organization, original_payment, adjustment_type, amount_delta, reason, created_by, timestamps

### 22.6 Reporting

**ReportExportJob:** organization, report_code, requested_by, parameters_json, status, output_attachment, created_at, completed_at, audit metadata

---

## 23. Recommended Django Project Layout

The layout below reflects the **Phase 1 Django-first** build. The Phase 2 additions (internal API app and React front-end directory) are noted inline and introduced when Phase 2 begins — they are not required to exist in Phase 1 but the layout anticipates them.

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
│   │   ├── landing/            # custom login landing page (Phase 1; retained in Phase 2)
│   │   ├── auth_portal/
│   │   └── tenant_portal/      # Django-templated tenant UI (Phase 1)
│   ├── crm/
│   │   ├── leads/
│   │   ├── quotes/
│   │   ├── clients/
│   │   ├── tasks/
│   │   ├── communications/
│   │   ├── orders/
│   │   └── billing/
│   ├── files/
│   │   └── attachments/
│   ├── reporting/
│   │   └── exports/
│   ├── catalog/
│   │   ├── services/
│   │   ├── products/
│   │   ├── materials/
│   │   ├── suppliers/
│   │   ├── pricing/
│   │   └── manufacturing/
│   ├── operations/
│   │   ├── locations/
│   │   ├── purchasing/
│   │   ├── build/
│   │   └── workorders/
│   ├── api/                    # Phase 2 — internal JSON API for React tenant portal
│   └── common/
│       ├── admin/
│       ├── tenancy/
│       ├── db/
│       ├── services/
│       ├── outbox/
│       ├── utils/
│       ├── choices/
│       └── tests/
├── templates/
├── static/
├── media/
├── frontend/                   # Phase 2 — React tenant-facing SPA source tree
├── requirements/
├── docker/
│   ├── django/
│   ├── postgres/
│   ├── nginx/
│   └── workers/
├── compose.yaml
└── .env.example
```

**Notes:**
- `apps/web/landing/` replaces the previously named `marketing/` directory to reflect the Phase 1 login-landing-page scope. A future marketing site can be added as a separate sub-app when/if approved.
- `apps/web/tenant_portal/` holds the Phase 1 server-rendered tenant UI. In Phase 2 it remains in place during transition and is retired only once the React client reaches feature parity.
- `apps/files/attachments/` owns permission-aware document and attachment workflows rather than scattering file fields across business apps.
- `apps/reporting/exports/` owns fixed reports and asynchronous export jobs only; it is not a generic analytics platform in v1.
- `apps/api/` is created at the start of Phase 2. It must not contain business logic — only request/response handling and service-layer invocation.
- `frontend/` is created at the start of Phase 2 and contains the React source tree. Its internal structure is defined in the Phase 2 design sprint.

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

### 24.3 Environment Requirements
The Docker-based environment must support:
- local development
- automated tests
- migration execution
- seed/bootstrap scripts
- background workers

### 24.3A Connection Pooling Posture
- pgBouncer is **required** in production environments.
- pgBouncer is optional in local development and automated test environments.
- Production deployment documentation must include connection-pool sizing guidance for web and worker processes.

### 24.4 Configuration Requirements
- Environment variables must drive config
- A checked-in `.env.example` is required
- Secrets must not be committed
- Per-environment settings modules must be supported

### 24.5 Confirmed Subdomain Development Strategy
Local development must include a reverse-proxy-based wildcard local domain strategy. Developers must be able to access the login landing page (root domain) and tenant portals locally using distinct hostnames. The chosen local domain pattern must be documented in onboarding/setup instructions.

### 24.6 Document and Media Storage Strategy
- Dev/test environments: local filesystem-backed storage
- Non-dev environments: **S3-compatible object storage** via `django-storages`
- The database stores file metadata and object references, not binary document contents
- Tenant-bound document access must be permission-aware
- Generated quote/invoice PDFs, completion photos, and uploaded files must use the same storage abstraction
- The storage abstraction must back the `DocumentAttachment` domain and support future malware-scanning and retention hooks

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

### 25.5 Transaction and Concurrency Requirements
All state-changing service methods affecting commercial, fulfillment, billing, or authorization records must execute inside explicit database transactions.

#### Required controls
- `accept_quote`, `record_payment`, `record_receipt`, entity numbering allocation, and fulfillment-generation services must use row-level locking and/or equivalent transactional safeguards.
- Mutable commercial records exposed to concurrent editing should support optimistic concurrency controls or equivalent stale-write detection.
- Celery tasks that create or transition business records must be safe to retry without creating duplicate business artifacts.
- Number generation must be atomic per organization, per entity type, and per calendar year.
- Duplicate form submissions or repeated API calls must fail safely or return the already-created result for idempotent operations.

### 25.6 Soft Delete Policy
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
- Region / Market / Location scope assignment changes
- quote acceptance
- pricing overrides
- task creation / assignment / completion / cancellation
- communication logging and outbound communication sends
- sales order creation
- PO/build/work-order generation
- invoice/payment updates
- role/capability changes
- all state transitions on workflow entities

### 26.1A Audit Payload and Retention Policy
- `AuditEvent` is append-only.
- Audit payloads must capture enough metadata to reconstruct who acted, on what object, in which organization, and under which impersonation context.
- Audit payloads must not store raw passwords, reset tokens, secrets, or other sensitive credentials.
- Before/after payloads must follow masking/redaction rules for sensitive or high-volume fields.
- Audit retention and export requirements must be documented before first production launch.

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
- tenant-local logout vs root-domain logout behavior
- Region / Market / Location operating-scope enforcement
- quote-to-order conversion
- PO/build/work-order generation
- task and communication workflows
- document-attachment authorization and storage abstraction behavior
- pricing calculations (unit tests with known inputs and expected outputs)
- pricing snapshot replay (replay must match original calculation)
- RBAC enforcement (capability coverage test: every URL pattern has a required_capability or is explicitly exempted)
- impersonation safeguards and audit attribution
- invoice/payment tracking basics, including payment reversal/adjustment behavior
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
- Role/capability enforcement by org and by Region / Market / Location scope
- Support impersonation audit logging with correct actor/on_behalf_of attribution
- Idempotency of fulfillment generation tasks
- Deterministic billing totals, tax calculations, and payment allocation behavior
- Logout/session behavior across root and tenant subdomains
- Attachment authorization and access control

---

## 28. Observability and Operations Requirements

### 28.1 Minimum Operational Visibility
- structured JSON logging
- application error monitoring
- worker error monitoring
- basic health checks
- migration visibility in deployment workflows

### 28.2 Confirmed Monitoring Baseline
- Structured JSON logging for application and worker processes
- Centralized application error monitoring before first tenant production launch
- Centralized worker error monitoring before first tenant production launch
- Health endpoints for core services
- Alertable visibility for critical async job failures
- OpenTelemetry remains an optional later expansion if distributed tracing needs expand

### 28.3 Backup, Restore, and Recovery Posture
- Automated database backups are required before first production launch.
- Restore procedures must be documented and exercised in a non-production environment.
- Recovery objectives (RPO/RTO) must be defined before onboarding the first production tenant.
- Object-storage recovery expectations for generated PDFs and uploaded attachments must be documented alongside database backup procedures.
