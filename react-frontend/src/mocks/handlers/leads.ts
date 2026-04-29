import {
    createLeadPayloadSchema,
    type CreateLeadPayload,
    type Lead,
} from '@features/leads/schema';
import { mockLeads } from '@mocks/data/leadsFixtures';
import { http, HttpResponse } from 'msw';

const API_BASE = '/api/internal';
const ORGANIZATION_ID = 'org-mph-demo';

function nextLeadNumber() {
  return mockLeads.length + 1;
}

function createLeadFromPayload(payload: CreateLeadPayload): Lead {
  const sequence = nextLeadNumber();
  const leadId = `lead-${String(sequence).padStart(3, '0')}`;
  const now = new Date().toISOString();

  return {
    id: leadId,
    organizationId: ORGANIZATION_ID,
    region: payload.region || null,
    market: payload.market || null,
    location: payload.location || null,
    leadNumber: `LD-2026-${String(sequence).padStart(5, '0')}`,
    source: payload.source,
    status: 'New',
    owner: {
      id: `user-${payload.ownerName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
      name: payload.ownerName,
    },
    companyName: payload.companyName,
    opportunityName: payload.opportunityName,
    estimatedSalesPrice: payload.estimatedSalesPrice,
    priority: payload.priority,
    summary: payload.summary,
    createdAt: now,
    updatedAt: now,
    contacts: [
      {
        id: `lead-contact-${String(sequence).padStart(3, '0')}`,
        leadId,
        name: payload.contact.name,
        email: payload.contact.email,
        phone: payload.contact.phone,
        roleTitle: payload.contact.roleTitle,
      },
    ],
    locations: [
      {
        id: `lead-location-${String(sequence).padStart(3, '0')}`,
        leadId,
        addressLine1: payload.locationAddress.addressLine1,
        addressLine2: payload.locationAddress.addressLine2 || null,
        city: payload.locationAddress.city,
        state: payload.locationAddress.state,
        postalCode: payload.locationAddress.postalCode,
        locationNotes: payload.locationAddress.locationNotes || null,
      },
    ],
  };
}

export const leadsHandlers = [
  http.get(`${API_BASE}/leads/`, ({ request }) => {
    const url = new URL(request.url);

    const search = url.searchParams.get('search')?.trim().toLowerCase() ?? '';
    const status = url.searchParams.get('status') ?? '';
    const source = url.searchParams.get('source') ?? '';
    const ownerId = url.searchParams.get('ownerId') ?? '';

    let results = [...mockLeads];

    if (search) {
      results = results.filter((lead) => {
        return (
          lead.companyName.toLowerCase().includes(search) ||
          lead.opportunityName.toLowerCase().includes(search) ||
          lead.leadNumber.toLowerCase().includes(search) ||
          lead.owner.name.toLowerCase().includes(search) ||
          lead.market?.toLowerCase().includes(search)
        );
      });
    }

    if (status) {
      results = results.filter((lead) => lead.status === status);
    }

    if (source) {
      results = results.filter((lead) => lead.source === source);
    }

    if (ownerId) {
      results = results.filter((lead) => lead.owner.id === ownerId);
    }

    results.sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    );

    return HttpResponse.json({
      count: results.length,
      results,
    });
  }),

  http.post(`${API_BASE}/leads/`, async ({ request }) => {
    const body = await request.json();
    const parsed = createLeadPayloadSchema.safeParse(body);

    if (!parsed.success) {
      return HttpResponse.json(
        {
          detail: 'Validation failed.',
          issues: parsed.error.flatten(),
        },
        { status: 400 },
      );
    }

    const createdLead = createLeadFromPayload(parsed.data);

    mockLeads.unshift(createdLead);

    return HttpResponse.json(createdLead, { status: 201 });
  }),

  http.get(`${API_BASE}/leads/:leadId/`, ({ params }) => {
    const lead = mockLeads.find((item) => item.id === params.leadId);

    if (!lead) {
      return HttpResponse.json(
        {
          detail: 'Lead not found.',
        },
        { status: 404 },
      );
    }

    return HttpResponse.json(lead);
  }),
];