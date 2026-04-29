import type {
    Lead,
    LeadPriority,
    LeadSource,
    LeadStatus,
} from '@features/leads/schema';

type MockLeadInput = {
  region: string | null;
  market: string | null;
  location: string | null;
  source: LeadSource;
  status: LeadStatus;
  owner: {
    id: string;
    name: string;
  };
  companyName: string;
  opportunityName: string;
  estimatedSalesPrice: number;
  priority: LeadPriority;
  summary: string;
  createdAt: string;
  updatedAt: string;
  contact: {
    name: string;
    email: string;
    phone: string;
    roleTitle: string;
  };
  address: {
    addressLine1: string;
    addressLine2?: string | null;
    city: string;
    state: string;
    postalCode: string;
    locationNotes?: string | null;
  };
};

const ORGANIZATION_ID = 'org-mph-demo';

function createMockLead(index: number, input: MockLeadInput): Lead {
  const id = `lead-${String(index).padStart(3, '0')}`;
  const contactId = `lead-contact-${String(index).padStart(3, '0')}`;
  const locationId = `lead-location-${String(index).padStart(3, '0')}`;

  return {
    id,
    organizationId: ORGANIZATION_ID,
    region: input.region,
    market: input.market,
    location: input.location,
    leadNumber: `LD-2026-${String(index).padStart(5, '0')}`,
    source: input.source,
    status: input.status,
    owner: input.owner,
    companyName: input.companyName,
    opportunityName: input.opportunityName,
    estimatedSalesPrice: input.estimatedSalesPrice,
    priority: input.priority,
    summary: input.summary,
    createdAt: input.createdAt,
    updatedAt: input.updatedAt,
    contacts: [
      {
        id: contactId,
        leadId: id,
        name: input.contact.name,
        email: input.contact.email,
        phone: input.contact.phone,
        roleTitle: input.contact.roleTitle,
      },
    ],
    locations: [
      {
        id: locationId,
        leadId: id,
        addressLine1: input.address.addressLine1,
        addressLine2: input.address.addressLine2 ?? null,
        city: input.address.city,
        state: input.address.state,
        postalCode: input.address.postalCode,
        locationNotes: input.address.locationNotes ?? null,
      },
    ],
  };
}

export const mockLeads: Lead[] = [
  createMockLead(1, {
    region: 'North',
    market: 'Chicago',
    location: 'Chicago HQ',
    source: 'Website',
    status: 'New',
    owner: { id: 'user-001', name: 'Alex Morgan' },
    companyName: 'Summit Facilities Group',
    opportunityName: 'Multi-site maintenance contract',
    estimatedSalesPrice: 48500,
    priority: 'High',
    summary:
      'Interested in recurring facility maintenance across four regional offices.',
    createdAt: '2026-01-08T14:12:00Z',
    updatedAt: '2026-04-21T10:30:00Z',
    contact: {
      name: 'Dana Reynolds',
      email: 'dana.reynolds@summitfacilities.example',
      phone: '(312) 555-0148',
      roleTitle: 'Operations Director',
    },
    address: {
      addressLine1: '155 W Monroe St',
      city: 'Chicago',
      state: 'IL',
      postalCode: '60603',
      locationNotes: 'Main office; ask security for loading dock access.',
    },
  }),

  createMockLead(2, {
    region: 'North',
    market: 'Milwaukee',
    location: 'Milwaukee Field Office',
    source: 'Referral',
    status: 'Contacted',
    owner: { id: 'user-002', name: 'Marcus Green' },
    companyName: 'Brightline Kitchens',
    opportunityName: 'Custom production line buildout',
    estimatedSalesPrice: 72500,
    priority: 'Urgent',
    summary:
      'Needs custom fabrication and installation for a new commercial kitchen line.',
    createdAt: '2026-01-19T09:20:00Z',
    updatedAt: '2026-04-20T15:15:00Z',
    contact: {
      name: 'Elena Park',
      email: 'elena.park@brightlinekitchens.example',
      phone: '(414) 555-0189',
      roleTitle: 'Project Manager',
    },
    address: {
      addressLine1: '800 N Water St',
      city: 'Milwaukee',
      state: 'WI',
      postalCode: '53202',
      locationNotes: 'Construction site access requires hard hat.',
    },
  }),

  createMockLead(3, {
    region: 'South',
    market: 'Austin',
    location: 'Austin Central',
    source: 'Trade Show',
    status: 'Qualified',
    owner: { id: 'user-003', name: 'Priya Shah' },
    companyName: 'Cedar Ridge Builders',
    opportunityName: 'Service and resale product bundle',
    estimatedSalesPrice: 39250,
    priority: 'Medium',
    summary:
      'Looking for installation services plus resale equipment procurement.',
    createdAt: '2026-02-01T11:05:00Z',
    updatedAt: '2026-04-19T13:44:00Z',
    contact: {
      name: 'Tom Keller',
      email: 'tom.keller@cedarridge.example',
      phone: '(512) 555-0133',
      roleTitle: 'Estimator',
    },
    address: {
      addressLine1: '220 Congress Ave',
      city: 'Austin',
      state: 'TX',
      postalCode: '78701',
      locationNotes: 'Initial walkthrough requested.',
    },
  }),

  createMockLead(4, {
    region: 'West',
    market: 'Denver',
    location: 'Denver Metro',
    source: 'Cold Outreach',
    status: 'New',
    owner: { id: 'user-001', name: 'Alex Morgan' },
    companyName: 'Peakline Logistics',
    opportunityName: 'Warehouse service program',
    estimatedSalesPrice: 18800,
    priority: 'Low',
    summary:
      'Exploring quarterly service options for warehouse locations.',
    createdAt: '2026-02-07T08:40:00Z',
    updatedAt: '2026-04-17T16:22:00Z',
    contact: {
      name: 'Jordan Miles',
      email: 'jordan.miles@peakline.example',
      phone: '(720) 555-0192',
      roleTitle: 'Facilities Manager',
    },
    address: {
      addressLine1: '1440 Blake St',
      city: 'Denver',
      state: 'CO',
      postalCode: '80202',
    },
  }),

  createMockLead(5, {
    region: 'East',
    market: 'Charlotte',
    location: 'Charlotte North',
    source: 'Existing Client',
    status: 'Qualified',
    owner: { id: 'user-004', name: 'Nina Brooks' },
    companyName: 'Harbor & Pine Hospitality',
    opportunityName: 'Renovation support package',
    estimatedSalesPrice: 56600,
    priority: 'High',
    summary:
      'Hospitality group needs several phases of service and manufactured items.',
    createdAt: '2026-02-13T12:10:00Z',
    updatedAt: '2026-04-22T09:05:00Z',
    contact: {
      name: 'Mia Campbell',
      email: 'mia.campbell@harborpine.example',
      phone: '(704) 555-0166',
      roleTitle: 'Regional Manager',
    },
    address: {
      addressLine1: '300 S Tryon St',
      city: 'Charlotte',
      state: 'NC',
      postalCode: '28202',
    },
  }),

  createMockLead(6, {
    region: 'South',
    market: 'Dallas',
    location: 'Dallas Central',
    source: 'Website',
    status: 'Contacted',
    owner: { id: 'user-002', name: 'Marcus Green' },
    companyName: 'MetroCare Clinics',
    opportunityName: 'Clinic equipment installation',
    estimatedSalesPrice: 31400,
    priority: 'Medium',
    summary:
      'Needs equipment installation and follow-up service at three clinics.',
    createdAt: '2026-02-20T10:30:00Z',
    updatedAt: '2026-04-18T11:58:00Z',
    contact: {
      name: 'Rachel Nguyen',
      email: 'rachel.nguyen@metrocare.example',
      phone: '(214) 555-0109',
      roleTitle: 'Procurement Lead',
    },
    address: {
      addressLine1: '1910 Pacific Ave',
      city: 'Dallas',
      state: 'TX',
      postalCode: '75201',
    },
  }),

  createMockLead(7, {
    region: 'West',
    market: 'Phoenix',
    location: 'Phoenix East',
    source: 'Partner',
    status: 'Unqualified',
    owner: { id: 'user-003', name: 'Priya Shah' },
    companyName: 'Saguaro Retail Group',
    opportunityName: 'Store remodel quote',
    estimatedSalesPrice: 9200,
    priority: 'Low',
    summary: 'Budget does not appear aligned with project scope.',
    createdAt: '2026-02-26T15:24:00Z',
    updatedAt: '2026-04-16T12:00:00Z',
    contact: {
      name: 'Chris Moreno',
      email: 'chris.moreno@saguaroretail.example',
      phone: '(602) 555-0175',
      roleTitle: 'Store Operations',
    },
    address: {
      addressLine1: '40 N Central Ave',
      city: 'Phoenix',
      state: 'AZ',
      postalCode: '85004',
    },
  }),

  createMockLead(8, {
    region: 'North',
    market: 'Minneapolis',
    location: 'Twin Cities',
    source: 'Inbound Call',
    status: 'New',
    owner: { id: 'user-004', name: 'Nina Brooks' },
    companyName: 'Northstar Manufacturing',
    opportunityName: 'Custom part fabrication',
    estimatedSalesPrice: 64800,
    priority: 'High',
    summary:
      'Custom manufactured product inquiry with recurring volume potential.',
    createdAt: '2026-03-02T09:11:00Z',
    updatedAt: '2026-04-21T14:25:00Z',
    contact: {
      name: 'Ben Holloway',
      email: 'ben.holloway@northstarmfg.example',
      phone: '(612) 555-0157',
      roleTitle: 'Plant Manager',
    },
    address: {
      addressLine1: '90 S 7th St',
      city: 'Minneapolis',
      state: 'MN',
      postalCode: '55402',
    },
  }),

  createMockLead(9, {
    region: 'East',
    market: 'Atlanta',
    location: 'Atlanta South',
    source: 'Website',
    status: 'Qualified',
    owner: { id: 'user-001', name: 'Alex Morgan' },
    companyName: 'Oak & Ember Restaurants',
    opportunityName: 'Restaurant group service agreement',
    estimatedSalesPrice: 27600,
    priority: 'Medium',
    summary:
      'Multi-location restaurant maintenance and small project work.',
    createdAt: '2026-03-06T13:00:00Z',
    updatedAt: '2026-04-23T10:00:00Z',
    contact: {
      name: 'Lauren Hill',
      email: 'lauren.hill@oakember.example',
      phone: '(404) 555-0182',
      roleTitle: 'Owner',
    },
    address: {
      addressLine1: '75 Peachtree Pl',
      city: 'Atlanta',
      state: 'GA',
      postalCode: '30309',
    },
  }),

  createMockLead(10, {
    region: 'West',
    market: 'Seattle',
    location: 'Seattle North',
    source: 'Trade Show',
    status: 'Contacted',
    owner: { id: 'user-002', name: 'Marcus Green' },
    companyName: 'Evergreen Workspace',
    opportunityName: 'Office refresh services',
    estimatedSalesPrice: 22400,
    priority: 'Medium',
    summary:
      'Office refresh with installation and procurement requirements.',
    createdAt: '2026-03-11T16:05:00Z',
    updatedAt: '2026-04-20T08:36:00Z',
    contact: {
      name: 'Sam Ito',
      email: 'sam.ito@evergreenworkspace.example',
      phone: '(206) 555-0130',
      roleTitle: 'Workplace Manager',
    },
    address: {
      addressLine1: '500 Union St',
      city: 'Seattle',
      state: 'WA',
      postalCode: '98101',
    },
  }),

  createMockLead(11, {
    region: 'South',
    market: 'Houston',
    location: 'Houston West',
    source: 'Referral',
    status: 'Converted',
    owner: { id: 'user-003', name: 'Priya Shah' },
    companyName: 'Gulfstream Industrial',
    opportunityName: 'Accepted service quote',
    estimatedSalesPrice: 81200,
    priority: 'High',
    summary: 'Converted to quote and accepted for service fulfillment.',
    createdAt: '2026-03-13T10:15:00Z',
    updatedAt: '2026-04-23T15:12:00Z',
    contact: {
      name: 'Andre Wilson',
      email: 'andre.wilson@gulfstreamindustrial.example',
      phone: '(713) 555-0144',
      roleTitle: 'Facilities Lead',
    },
    address: {
      addressLine1: '1001 Fannin St',
      city: 'Houston',
      state: 'TX',
      postalCode: '77002',
    },
  }),

  createMockLead(12, {
    region: 'East',
    market: 'Raleigh',
    location: 'Raleigh Durham',
    source: 'Cold Outreach',
    status: 'New',
    owner: { id: 'user-004', name: 'Nina Brooks' },
    companyName: 'Triangle Lab Services',
    opportunityName: 'Lab equipment setup',
    estimatedSalesPrice: 33100,
    priority: 'Medium',
    summary:
      'New lab setup requiring service, purchased products, and documentation.',
    createdAt: '2026-03-16T08:55:00Z',
    updatedAt: '2026-04-19T09:45:00Z',
    contact: {
      name: 'Vanessa Lee',
      email: 'vanessa.lee@trianglelab.example',
      phone: '(919) 555-0111',
      roleTitle: 'Lab Administrator',
    },
    address: {
      addressLine1: '301 Hillsborough St',
      city: 'Raleigh',
      state: 'NC',
      postalCode: '27603',
    },
  }),

  createMockLead(13, {
    region: 'North',
    market: 'Detroit',
    location: 'Detroit Metro',
    source: 'Partner',
    status: 'Qualified',
    owner: { id: 'user-001', name: 'Alex Morgan' },
    companyName: 'Motor City Components',
    opportunityName: 'Manufactured component quote',
    estimatedSalesPrice: 104000,
    priority: 'Urgent',
    summary: 'High-value manufactured product quote with BOM review required.',
    createdAt: '2026-03-18T12:40:00Z',
    updatedAt: '2026-04-23T12:30:00Z',
    contact: {
      name: 'Derek Collins',
      email: 'derek.collins@motorcitycomponents.example',
      phone: '(313) 555-0191',
      roleTitle: 'Engineering Manager',
    },
    address: {
      addressLine1: '211 W Fort St',
      city: 'Detroit',
      state: 'MI',
      postalCode: '48226',
    },
  }),

  createMockLead(14, {
    region: 'West',
    market: 'Portland',
    location: 'Portland Central',
    source: 'Website',
    status: 'Archived',
    owner: { id: 'user-002', name: 'Marcus Green' },
    companyName: 'Cascade Wellness',
    opportunityName: 'Small equipment installation',
    estimatedSalesPrice: 6400,
    priority: 'Low',
    summary: 'Archived after no response from primary contact.',
    createdAt: '2026-03-21T09:33:00Z',
    updatedAt: '2026-04-22T17:08:00Z',
    contact: {
      name: 'Olivia Grant',
      email: 'olivia.grant@cascadewellness.example',
      phone: '(503) 555-0152',
      roleTitle: 'Office Manager',
    },
    address: {
      addressLine1: '555 SW Morrison St',
      city: 'Portland',
      state: 'OR',
      postalCode: '97204',
    },
  }),

  createMockLead(15, {
    region: 'South',
    market: 'Nashville',
    location: 'Nashville Metro',
    source: 'Inbound Call',
    status: 'Contacted',
    owner: { id: 'user-003', name: 'Priya Shah' },
    companyName: 'Volunteer Event Venues',
    opportunityName: 'Venue maintenance program',
    estimatedSalesPrice: 41200,
    priority: 'High',
    summary:
      'Event venue group requesting recurring maintenance and fast response options.',
    createdAt: '2026-03-25T14:18:00Z',
    updatedAt: '2026-04-23T08:15:00Z',
    contact: {
      name: 'Patrick Lane',
      email: 'patrick.lane@volunteervenues.example',
      phone: '(615) 555-0184',
      roleTitle: 'General Manager',
    },
    address: {
      addressLine1: '401 Broadway',
      city: 'Nashville',
      state: 'TN',
      postalCode: '37203',
    },
  }),

  createMockLead(16, {
    region: 'East',
    market: 'Boston',
    location: 'Boston Harbor',
    source: 'Existing Client',
    status: 'Qualified',
    owner: { id: 'user-004', name: 'Nina Brooks' },
    companyName: 'HarborPoint Offices',
    opportunityName: 'Tenant improvement support',
    estimatedSalesPrice: 59800,
    priority: 'High',
    summary:
      'Office tenant improvement requiring services and document attachments.',
    createdAt: '2026-03-28T11:25:00Z',
    updatedAt: '2026-04-23T16:20:00Z',
    contact: {
      name: 'Grace Patel',
      email: 'grace.patel@harborpoint.example',
      phone: '(617) 555-0116',
      roleTitle: 'Property Manager',
    },
    address: {
      addressLine1: '1 Seaport Ln',
      city: 'Boston',
      state: 'MA',
      postalCode: '02210',
    },
  }),

  createMockLead(17, {
    region: 'North',
    market: 'Indianapolis',
    location: 'Indianapolis Central',
    source: 'Referral',
    status: 'New',
    owner: { id: 'user-001', name: 'Alex Morgan' },
    companyName: 'Circle City Distribution',
    opportunityName: 'Distribution center repair work',
    estimatedSalesPrice: 26750,
    priority: 'Medium',
    summary: 'Needs quote for several repairs and possible replacement products.',
    createdAt: '2026-04-02T13:41:00Z',
    updatedAt: '2026-04-21T11:35:00Z',
    contact: {
      name: 'Sean Peters',
      email: 'sean.peters@circlecitydist.example',
      phone: '(317) 555-0127',
      roleTitle: 'Warehouse Manager',
    },
    address: {
      addressLine1: '111 Monument Cir',
      city: 'Indianapolis',
      state: 'IN',
      postalCode: '46204',
    },
  }),

  createMockLead(18, {
    region: 'West',
    market: 'San Diego',
    location: 'San Diego Coastal',
    source: 'Website',
    status: 'Contacted',
    owner: { id: 'user-002', name: 'Marcus Green' },
    companyName: 'Pacific Dental Partners',
    opportunityName: 'Clinic refresh project',
    estimatedSalesPrice: 44300,
    priority: 'Medium',
    summary: 'Clinic group evaluating phased refresh across two locations.',
    createdAt: '2026-04-08T10:02:00Z',
    updatedAt: '2026-04-22T13:14:00Z',
    contact: {
      name: 'Isabella Ross',
      email: 'isabella.ross@pacificdental.example',
      phone: '(619) 555-0172',
      roleTitle: 'Practice Administrator',
    },
    address: {
      addressLine1: '600 W Broadway',
      city: 'San Diego',
      state: 'CA',
      postalCode: '92101',
    },
  }),

  createMockLead(19, {
    region: 'South',
    market: 'Tampa',
    location: 'Tampa Bay',
    source: 'Trade Show',
    status: 'Qualified',
    owner: { id: 'user-003', name: 'Priya Shah' },
    companyName: 'Bayfront Fitness Group',
    opportunityName: 'Multi-location equipment install',
    estimatedSalesPrice: 68750,
    priority: 'High',
    summary:
      'Fitness group needs equipment procurement, install, and service package.',
    createdAt: '2026-04-14T15:55:00Z',
    updatedAt: '2026-04-23T09:52:00Z',
    contact: {
      name: 'Noah Bennett',
      email: 'noah.bennett@bayfrontfitness.example',
      phone: '(813) 555-0161',
      roleTitle: 'Expansion Lead',
    },
    address: {
      addressLine1: '401 E Jackson St',
      city: 'Tampa',
      state: 'FL',
      postalCode: '33602',
    },
  }),

  createMockLead(20, {
    region: 'East',
    market: 'Philadelphia',
    location: 'Philadelphia Central',
    source: 'Partner',
    status: 'New',
    owner: { id: 'user-004', name: 'Nina Brooks' },
    companyName: 'Keystone Property Services',
    opportunityName: 'Property portfolio maintenance',
    estimatedSalesPrice: 52100,
    priority: 'High',
    summary: 'Portfolio maintenance opportunity with possible recurring contract.',
    createdAt: '2026-04-20T12:05:00Z',
    updatedAt: '2026-04-23T14:10:00Z',
    contact: {
      name: 'Avery Stone',
      email: 'avery.stone@keystoneproperty.example',
      phone: '(215) 555-0141',
      roleTitle: 'Asset Manager',
    },
    address: {
      addressLine1: '1700 Market St',
      city: 'Philadelphia',
      state: 'PA',
      postalCode: '19103',
    },
  }),
];