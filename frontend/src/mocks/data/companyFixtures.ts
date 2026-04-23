import type { CompanySummary } from '@/features/companies/api/queries';
import type { MockScenarioKey } from '@/lib/dev/mockState';

const ownerCompanies: CompanySummary[] = [
  {
    id: 'cmp_001',
    name: 'Cedar Ridge Estates',
    status: 'active',
    industry: 'Property management',
    owner_name: 'Riley Owner',
    primary_contact_name: 'Jordan Blake',
    primary_contact_email: 'jordan@cedarridge.test',
    created_at: '2026-04-01T15:20:00Z',
    updated_at: '2026-04-22T18:10:00Z',
  },
  {
    id: 'cmp_002',
    name: 'Bluebird Retail Group',
    status: 'active',
    industry: 'Retail',
    owner_name: 'Casey Sellers',
    primary_contact_name: 'Taylor Moss',
    primary_contact_email: 'taylor@bluebirdretail.test',
    created_at: '2026-03-18T12:00:00Z',
    updated_at: '2026-04-21T14:50:00Z',
  },
  {
    id: 'cmp_003',
    name: 'Northwind Packaging',
    status: 'inactive',
    industry: 'Manufacturing',
    owner_name: 'Riley Owner',
    primary_contact_name: 'Avery Finch',
    primary_contact_email: 'avery@northwind.test',
    created_at: '2026-02-11T09:30:00Z',
    updated_at: '2026-04-19T11:15:00Z',
  },
  {
    id: 'cmp_004',
    name: 'Summit Dental Partners',
    status: 'active',
    industry: 'Healthcare',
    owner_name: 'Jamie Quinn',
    primary_contact_name: 'Parker Lane',
    primary_contact_email: 'parker@summitdental.test',
    created_at: '2026-01-22T16:45:00Z',
    updated_at: '2026-04-23T08:05:00Z',
  },
  {
    id: 'cmp_005',
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
    id: 'cmp_006',
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
    id: 'cmp_007',
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
    id: 'cmp_008',
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
    id: 'cmp_009',
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
    id: 'cmp_010',
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
    id: 'cmp_011',
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
    id: 'cmp_012',
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

const impersonationCompanies: CompanySummary[] = [
  {
    id: 'cmp_b1',
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
    id: 'cmp_b2',
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

export function getCompaniesFixture(scenario: MockScenarioKey): CompanySummary[] {
  switch (scenario) {
    case 'viewer':
    case 'owner':
    case 'companies-error':
      return ownerCompanies;
    case 'impersonating':
      return impersonationCompanies;
    case 'companies-empty':
    case 'logged-out':
      return [];
    default:
      return ownerCompanies;
  }
}
