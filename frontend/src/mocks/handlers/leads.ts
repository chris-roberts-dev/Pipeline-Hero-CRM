import { http, HttpResponse } from 'msw';
import type { CreateLeadPayload, Lead } from '../../features/leads/types';
import { mockLeads } from '../data/leadsFixtures';

const API_BASE = '/api/internal';
const ORGANIZATION_ID = 'org-acme';

function nextLeadSequence() {
  return mockLeads.length + 1;
}

function createLeadFromPayload(payload: CreateLeadPayload): Lead {
  const sequence = nextLeadSequence();
  const paddedSequence = String(sequence).padStart(5, '0');
  const leadId = `lead-${String(sequence).padStart(3, '0')}`;
  const now = new Date().toISOString();

  return {
    id: leadId,
    organizationId: ORGANIZATION_ID,
    region: payload.region || null,
    market: payload.market || null,
    location: payload.location || null,
    leadNumber: `LD-2026-${paddedSequence}`,
    source: payload.source,
    status: 'New',
    owner: {
      id: `user-${payload.ownerName.toLowerCase().replace(/\s+/g, '-')}`,
      name: payload.ownerName,
    },
    companyName: payload.companyName,
    opportunityName: payload.opportunityName,
    estimatedValue: payload.estimatedValue,
    priority: payload.priority,
    summary: payload.summary,
    createdAt: now,
    updatedAt: now,
    contacts: [
      {
        id: `contact-${String(sequence).padStart(3, '0')}`,
        leadId,
        name: payload.contact.name,
        email: payload.contact.email,
        phone: payload.contact.phone,
        roleTitle: payload.contact.roleTitle,
      },
    ],
    locations: [
      {
        id: `loc-${String(sequence).padStart(3, '0')}`,
        leadId,
        addressLine1: payload.locationAddress.addressLine1,
        addressLine2: payload.locationAddress.addressLine2,
        city: payload.locationAddress.city,
        state: payload.locationAddress.state,
        postalCode: payload.locationAddress.postalCode,
        locationNotes: payload.locationAddress.locationNotes,
      },
    ],
  };
}

function validatePayload(payload: Partial<CreateLeadPayload>) {
  if (!payload.companyName?.trim()) return 'Company name is required.';
  if (!payload.opportunityName?.trim()) return 'Opportunity name is required.';
  if (!payload.source?.trim()) return 'Lead source is required.';
  if (!payload.ownerName?.trim()) return 'Owner is required.';
  if (!payload.summary?.trim()) return 'Summary is required.';
  if (!payload.estimatedValue || payload.estimatedValue < 0) {
    return 'Estimated value must be zero or greater.';
  }
  if (!payload.contact?.name?.trim()) return 'Primary contact name is required.';
  if (!payload.contact?.email?.trim()) return 'Primary contact email is required.';
  if (!payload.locationAddress?.addressLine1?.trim()) return 'Address line 1 is required.';
  if (!payload.locationAddress?.city?.trim()) return 'City is required.';
  if (!payload.locationAddress?.state?.trim()) return 'State is required.';
  if (!payload.locationAddress?.postalCode?.trim()) return 'Postal code is required.';

  return null;
}

export const leadsHandlers = [
  http.get(`${API_BASE}/leads/`, ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search')?.toLowerCase() ?? '';
    const status = url.searchParams.get('status') ?? '';

    let results = [...mockLeads];

    if (search) {
      results = results.filter((lead) => {
        return (
          lead.companyName.toLowerCase().includes(search) ||
          lead.opportunityName.toLowerCase().includes(search) ||
          lead.leadNumber.toLowerCase().includes(search) ||
          lead.owner.name.toLowerCase().includes(search)
        );
      });
    }

    if (status) {
      results = results.filter((lead) => lead.status === status);
    }

    return HttpResponse.json({
      count: results.length,
      results,
    });
  }),

  http.post(`${API_BASE}/leads/`, async ({ request }) => {
    const payload = (await request.json()) as CreateLeadPayload;
    const validationError = validatePayload(payload);

    if (validationError) {
      return HttpResponse.json(
        { detail: validationError },
        { status: 400 },
      );
    }

    const createdLead = createLeadFromPayload(payload);

    mockLeads.unshift(createdLead);

    return HttpResponse.json(createdLead, { status: 201 });
  }),

  http.get(`${API_BASE}/leads/:leadId/`, ({ params }) => {
    const lead = mockLeads.find((item) => item.id === params.leadId);

    if (!lead) {
      return HttpResponse.json(
        { detail: 'Lead not found.' },
        { status: 404 },
      );
    }

    return HttpResponse.json(lead);
  }),
];