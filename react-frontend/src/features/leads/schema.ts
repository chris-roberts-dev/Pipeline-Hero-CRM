import { z } from 'zod';

export const leadStatusSchema = z.enum([
  'New',
  'Contacted',
  'Qualified',
  'Unqualified',
  'Converted',
  'Archived',
]);

export const leadPrioritySchema = z.enum([
  'Low',
  'Medium',
  'High',
  'Urgent',
]);

export const leadSourceSchema = z.enum([
  'Website',
  'Referral',
  'Trade Show',
  'Cold Outreach',
  'Inbound Call',
  'Partner',
  'Existing Client',
]);

export const leadOwnerSchema = z.object({
  id: z.string(),
  name: z.string(),
});

export const leadContactSchema = z.object({
  id: z.string(),
  leadId: z.string(),
  name: z.string(),
  email: z.string().email(),
  phone: z.string(),
  roleTitle: z.string(),
});

export const leadLocationSchema = z.object({
  id: z.string(),
  leadId: z.string(),
  addressLine1: z.string(),
  addressLine2: z.string().nullable().optional(),
  city: z.string(),
  state: z.string(),
  postalCode: z.string(),
  locationNotes: z.string().nullable().optional(),
});

export const leadSchema = z.object({
  id: z.string(),
  organizationId: z.string(),
  region: z.string().nullable(),
  market: z.string().nullable(),
  location: z.string().nullable(),
  leadNumber: z.string(),
  source: leadSourceSchema,
  status: leadStatusSchema,
  owner: leadOwnerSchema,
  companyName: z.string(),
  opportunityName: z.string(),
  estimatedSalesPrice: z.number(),
  priority: leadPrioritySchema,
  summary: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  contacts: z.array(leadContactSchema),
  locations: z.array(leadLocationSchema),
});

export const leadsListResponseSchema = z.object({
  count: z.number(),
  results: z.array(leadSchema),
});

export const createLeadPayloadSchema = z.object({
  companyName: z.string().min(1, 'Company name is required.'),
  opportunityName: z.string().min(1, 'Opportunity name is required.'),
  source: leadSourceSchema,
  ownerName: z.string().min(1, 'Owner is required.'),
  region: z.string().nullable().optional(),
  market: z.string().nullable().optional(),
  location: z.string().nullable().optional(),
  estimatedSalesPrice: z.number().nonnegative(),
  priority: leadPrioritySchema,
  summary: z.string().min(1, 'Summary is required.'),

  contact: z.object({
    name: z.string().min(1, 'Primary contact name is required.'),
    email: z.string().email('A valid email is required.'),
    phone: z.string().min(1, 'Phone is required.'),
    roleTitle: z.string().min(1, 'Role/title is required.'),
  }),

  locationAddress: z.object({
    addressLine1: z.string().min(1, 'Address line 1 is required.'),
    addressLine2: z.string().nullable().optional(),
    city: z.string().min(1, 'City is required.'),
    state: z.string().min(1, 'State is required.'),
    postalCode: z.string().min(1, 'Postal code is required.'),
    locationNotes: z.string().nullable().optional(),
  }),
});

export type LeadStatus = z.infer<typeof leadStatusSchema>;
export type LeadPriority = z.infer<typeof leadPrioritySchema>;
export type LeadSource = z.infer<typeof leadSourceSchema>;
export type LeadOwner = z.infer<typeof leadOwnerSchema>;
export type LeadContact = z.infer<typeof leadContactSchema>;
export type LeadLocation = z.infer<typeof leadLocationSchema>;
export type Lead = z.infer<typeof leadSchema>;
export type LeadsListResponse = z.infer<typeof leadsListResponseSchema>;
export type CreateLeadPayload = z.infer<typeof createLeadPayloadSchema>;

export const leadStatuses = leadStatusSchema.options;
export const leadPriorities = leadPrioritySchema.options;
export const leadSources = leadSourceSchema.options;

export function isActiveLeadStatus(status: LeadStatus) {
  return status === 'New' || status === 'Contacted' || status === 'Qualified';
}