import type { SessionBootstrap } from '../../features/session/schema';

export const mockSession: SessionBootstrap = {
  isAuthenticated: true,

  user: {
    id: 'user-001',
    email: 'owner@mypipelinehero.test',
    fullName: 'Alex Morgan',
    avatarUrl: null,
    isPlatformOwner: true,
    isSupportUser: false,
  },

  activeOrganization: {
    id: 'org-mph-demo',
    name: 'MyPipelineHero Demo',
    slug: 'demo',
    tenantDomain: 'demo.mypipelinehero.local',
  },

  membership: {
    roleNames: ['Owner', 'Admin'],
    capabilityCodes: [
      'dashboard.view',
      'leads.view',
      'leads.create',
      'quotes.view',
      'clients.view',
      'orders.view',
      'settings.manage',
    ],
  },

  impersonation: {
    active: false,
    originalActorId: null,
    originalActorName: null,
    reason: null,
  },

  featureFlags: {
    leads: true,
    quotes: false,
    clients: false,
    orders: false,
    catalog: false,
  },
};

export const unauthenticatedSession: SessionBootstrap = {
  isAuthenticated: false,
  user: null,
  activeOrganization: null,
  membership: null,
  impersonation: null,
  featureFlags: {},
};