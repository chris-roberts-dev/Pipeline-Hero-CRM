import type { SessionBootstrap } from '@/lib/auth/types';
import type { MockScenarioKey } from '@/lib/dev/mockState';

const ownerSession: SessionBootstrap = {
  authenticated: true,
  organization: {
    id: 'org_acme',
    name: 'Acme Home Services',
    slug: 'acme',
    timezone: 'America/Chicago',
    base_currency_code: 'USD',
  },
  user: {
    id: 'user_owner_1',
    email: 'owner@acme.test',
    display_name: 'Riley Owner',
    is_support_user: false,
  },
  capabilities: [
    'clients.view',
    'clients.create',
    'clients.edit',
    'orders.view',
    'reporting.view',
    'admin.members.view',
  ],
  impersonation: {
    active: false,
    acting_as_email: null,
  },
};

const viewerSession: SessionBootstrap = {
  authenticated: true,
  organization: ownerSession.organization,
  user: {
    id: 'user_viewer_1',
    email: 'viewer@acme.test',
    display_name: 'Morgan Viewer',
    is_support_user: false,
  },
  capabilities: ['clients.view', 'orders.view'],
  impersonation: {
    active: false,
    acting_as_email: null,
  },
};

const impersonatingSession: SessionBootstrap = {
  authenticated: true,
  organization: {
    id: 'org_bluebird',
    name: 'Bluebird Mechanical',
    slug: 'bluebird',
    timezone: 'America/Denver',
    base_currency_code: 'USD',
  },
  user: {
    id: 'user_support_1',
    email: 'support@mypipelinehero.test',
    display_name: 'Alex Support',
    is_support_user: true,
  },
  capabilities: ['clients.view', 'clients.edit'],
  impersonation: {
    active: true,
    acting_as_email: 'ops.manager@bluebird.test',
  },
};

export function getSessionFixture(scenario: MockScenarioKey): SessionBootstrap | null {
  switch (scenario) {
    case 'viewer':
      return viewerSession;
    case 'impersonating':
      return impersonatingSession;
    case 'logged-out':
      return null;
    case 'organizations-empty':
    case 'organizations-error':
    case 'messages-empty':
    case 'messages-error':
    case 'notifications-empty':
    case 'notifications-error':
    case 'owner':
    default:
      return ownerSession;
  }
}
