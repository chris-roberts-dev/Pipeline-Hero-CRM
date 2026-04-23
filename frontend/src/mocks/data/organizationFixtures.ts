import type { OrganizationDetail, OrganizationSummary } from '@/features/organizations/api/queries';
import type { MockScenarioKey } from '@/lib/dev/mockState';

const ownerOrganizations: OrganizationSummary[] = [
  {
    id: 'org_001',
    name: 'Acme Industrial Services',
    status: 'active',
    industry: 'Facilities services',
    owner_name: 'Riley Owner',
    primary_contact_name: 'Morgan Lee',
    primary_contact_email: 'morgan@acme.test',
    created_at: '2026-02-10T15:30:00Z',
    updated_at: '2026-04-21T09:15:00Z',
  },
  {
    id: 'org_002',
    name: 'Bluebird Mechanical',
    status: 'active',
    industry: 'HVAC',
    owner_name: 'Jamie Quinn',
    primary_contact_name: 'Priya Singh',
    primary_contact_email: 'priya@bluebird.test',
    created_at: '2026-03-05T12:00:00Z',
    updated_at: '2026-04-23T07:30:00Z',
  },
  {
    id: 'org_003',
    name: 'Cedar Health Group',
    status: 'inactive',
    industry: 'Healthcare',
    owner_name: 'Jamie Quinn',
    primary_contact_name: 'Avery Chen',
    primary_contact_email: 'avery@cedarhealth.test',
    created_at: '2025-11-18T09:00:00Z',
    updated_at: '2026-04-18T11:45:00Z',
  },
  {
    id: 'org_004',
    name: 'Summit Dental Partners',
    status: 'active',
    industry: 'Dental',
    owner_name: 'Riley Owner',
    primary_contact_name: 'Jordan Parker',
    primary_contact_email: 'parker@summitdental.test',
    created_at: '2026-01-22T16:45:00Z',
    updated_at: '2026-04-23T08:05:00Z',
  },
  {
    id: 'org_005',
    name: 'Atlas Restoration',
    status: 'active',
    industry: 'Construction',
    owner_name: 'Casey Sellers',
    primary_contact_name: 'Rowan King',
    primary_contact_email: 'rowan@atlasrestore.test',
    created_at: '2025-12-14T13:05:00Z',
    updated_at: '2026-04-20T10:40:00Z',
  },
  {
    id: 'org_006',
    name: 'Riverstone Hospitality',
    status: 'inactive',
    industry: 'Hospitality',
    owner_name: 'Jamie Quinn',
    primary_contact_name: 'Harper Cole',
    primary_contact_email: 'harper@riverstone.test',
    created_at: '2025-11-09T17:25:00Z',
    updated_at: '2026-04-16T19:00:00Z',
  },
  {
    id: 'org_007',
    name: 'Granite Peak Logistics',
    status: 'active',
    industry: 'Logistics',
    owner_name: 'Riley Owner',
    primary_contact_name: 'Dakota Reed',
    primary_contact_email: 'dakota@granitepeak.test',
    created_at: '2026-04-03T14:00:00Z',
    updated_at: '2026-04-22T09:20:00Z',
  },
  {
    id: 'org_008',
    name: 'Lakeside Fitness Clubs',
    status: 'active',
    industry: 'Fitness',
    owner_name: 'Jamie Quinn',
    primary_contact_name: 'Blair Reese',
    primary_contact_email: 'blair@lakesidefit.test',
    created_at: '2026-03-01T07:55:00Z',
    updated_at: '2026-04-18T13:35:00Z',
  },
  {
    id: 'org_009',
    name: 'Harborline Marine',
    status: 'inactive',
    industry: 'Marine services',
    owner_name: 'Casey Sellers',
    primary_contact_name: 'Emerson Vale',
    primary_contact_email: 'emerson@harborline.test',
    created_at: '2025-10-28T20:10:00Z',
    updated_at: '2026-04-15T12:12:00Z',
  },
  {
    id: 'org_010',
    name: 'Pinecrest Schools',
    status: 'active',
    industry: 'Education',
    owner_name: 'Riley Owner',
    primary_contact_name: 'Skyler Webb',
    primary_contact_email: 'skyler@pinecrest.test',
    created_at: '2026-04-07T11:45:00Z',
    updated_at: '2026-04-23T06:55:00Z',
  },
  {
    id: 'org_011',
    name: 'Beacon Real Estate',
    status: 'active',
    industry: 'Real estate',
    owner_name: 'Jamie Quinn',
    primary_contact_name: 'Lane Porter',
    primary_contact_email: 'lane@beaconre.test',
    created_at: '2026-02-08T18:33:00Z',
    updated_at: '2026-04-17T17:07:00Z',
  },
  {
    id: 'org_012',
    name: 'Sterling Offices',
    status: 'inactive',
    industry: 'Commercial property',
    owner_name: 'Casey Sellers',
    primary_contact_name: 'Elliot Shaw',
    primary_contact_email: 'elliot@sterling.test',
    created_at: '2026-01-05T10:05:00Z',
    updated_at: '2026-04-12T09:41:00Z',
  },
];

const impersonationOrganizations: OrganizationSummary[] = [
  {
    id: 'org_b1',
    name: 'Bluebird Mechanical — Denver Ops',
    status: 'active',
    industry: 'HVAC',
    owner_name: 'Ops Manager',
    primary_contact_name: 'Priya Singh',
    primary_contact_email: 'priya@bluebird.test',
    created_at: '2026-03-05T15:00:00Z',
    updated_at: '2026-04-23T07:30:00Z',
  },
  {
    id: 'org_b2',
    name: 'Bluebird Mechanical — Service Contracts',
    status: 'active',
    industry: 'Service contracts',
    owner_name: 'Ops Manager',
    primary_contact_name: 'Luis Ortega',
    primary_contact_email: 'luis@bluebird.test',
    created_at: '2026-02-14T08:15:00Z',
    updated_at: '2026-04-20T16:00:00Z',
  },
];

function buildOrganizationDetails(organizations: OrganizationSummary[]): Record<string, OrganizationDetail> {
  return Object.fromEntries(
    organizations.map((organization, index) => {
      const revenueBase = 900000 + index * 175000;
      const employeeBase = 22 + index * 4;

      const detail: OrganizationDetail = {
        ...organization,
        website: `https://${organization.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.example.com`,
        phone: `(555) 01${String(index + 1).padStart(2, '0')}-4400`,
        lifecycle_stage: organization.status === 'active' ? 'customer' : 'former_customer',
        employee_count: employeeBase,
        annual_revenue: revenueBase,
        billing_address: `${120 + index} Market Street, Suite ${200 + index}, Chicago, IL 6060${index % 10}`,
        service_address: `${800 + index} Service Way, Dock ${index + 1}, Chicago, IL 6061${index % 10}`,
        notes: `${organization.name} is a high-value account used in the mock CRM to prove list-to-detail navigation before the backend is finished. Keep service-layer field names stable so the future Django endpoint can drop in cleanly.`,
        tags: [organization.status, organization.industry ?? 'general', index % 2 === 0 ? 'priority' : 'standard'],
        recent_activity: [
          {
            id: `${organization.id}_act_1`,
            title: 'Quote follow-up scheduled',
            description: `A follow-up task was queued for ${organization.primary_contact_name ?? 'the primary contact'} after the last pipeline review.`,
            time_label: '2 hours ago',
          },
          {
            id: `${organization.id}_act_2`,
            title: 'Organization record refreshed',
            description: `Ownership and contact details were reviewed by ${organization.owner_name ?? 'the assigned rep'}.`,
            time_label: 'Yesterday',
          },
          {
            id: `${organization.id}_act_3`,
            title: 'Discovery notes added',
            description: 'Implementation scope and regional servicing constraints were documented for the account team.',
            time_label: '3 days ago',
          },
        ],
      };
      return [organization.id, detail];
    }),
  );
}

const ownerOrganizationDetails = buildOrganizationDetails(ownerOrganizations);
const impersonationOrganizationDetails = buildOrganizationDetails(impersonationOrganizations);

export function getOrganizationsFixture(scenario: MockScenarioKey): OrganizationSummary[] {
  switch (scenario) {
    case 'viewer':
    case 'owner':
    case 'organizations-error':
      return ownerOrganizations;
    case 'impersonating':
      return impersonationOrganizations;
    case 'organizations-empty':
    case 'logged-out':
      return [];
    default:
      return ownerOrganizations;
  }
}

export function getOrganizationDetailFixture(scenario: MockScenarioKey, organizationId: string): OrganizationDetail | null {
  switch (scenario) {
    case 'viewer':
    case 'owner':
    case 'organizations-error':
      return ownerOrganizationDetails[organizationId] ?? null;
    case 'impersonating':
      return impersonationOrganizationDetails[organizationId] ?? null;
    case 'organizations-empty':
    case 'logged-out':
      return null;
    default:
      return ownerOrganizationDetails[organizationId] ?? null;
  }
}
