export type LeadStatus =
  | 'New'
  | 'Contacted'
  | 'Qualified'
  | 'Unqualified'
  | 'Converted'
  | 'Archived';

export type LeadPriority = 'Low' | 'Medium' | 'High' | 'Urgent';

export type LeadOwner = {
  id: string;
  name: string;
};

export type LeadContact = {
  id: string;
  leadId: string;
  name: string;
  email: string;
  phone: string;
  roleTitle: string;
};

export type LeadLocation = {
  id: string;
  leadId: string;
  addressLine1: string;
  addressLine2?: string;
  city: string;
  state: string;
  postalCode: string;
  locationNotes?: string;
};

export type Lead = {
  id: string;
  organizationId: string;
  region?: string | null;
  market?: string | null;
  location?: string | null;
  leadNumber: string;
  source: string;
  status: LeadStatus;
  owner: LeadOwner;
  companyName: string;
  opportunityName: string;
  estimatedValue: number;
  priority: LeadPriority;
  summary: string;
  createdAt: string;
  updatedAt: string;
  contacts: LeadContact[];
  locations: LeadLocation[];
};

export type CreateLeadPayload = {
  companyName: string;
  opportunityName: string;
  source: string;
  ownerName: string;
  region?: string | null;
  market?: string | null;
  location?: string | null;
  estimatedValue: number;
  priority: LeadPriority;
  summary: string;

  contact: {
    name: string;
    email: string;
    phone: string;
    roleTitle: string;
  };

  locationAddress: {
    addressLine1: string;
    addressLine2?: string;
    city: string;
    state: string;
    postalCode: string;
    locationNotes?: string;
  };
};

export type LeadsListResponse = {
  count: number;
  results: Lead[];
};