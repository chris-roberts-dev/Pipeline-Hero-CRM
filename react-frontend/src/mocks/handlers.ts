import { leadsHandlers } from '@mocks/handlers/leads';
import { http, HttpResponse } from 'msw';

const API_BASE = '/api/internal';

export const handlers = [
  ...leadsHandlers,
  http.get(`${API_BASE}/session/`, () => {
    return HttpResponse.json({
      isAuthenticated: true,
      user: {
        id: 'user-001',
        email: 'owner@mypipelinehero.test',
        fullName: 'Chris Roberts',
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
    });
  }),

  http.get(`${API_BASE}/messages/summary/`, () => {
    return HttpResponse.json({
      unreadCount: 3,
      items: [
        {
          id: 'msg-001',
          sender: 'Dana Reynolds',
          preview: 'Can you review the new quote request?',
          timeLabel: '12 mins ago',
          href: '#',
          avatarInitials: 'DR',
          starred: true,
          tone: 'danger',
        },
        {
          id: 'msg-002',
          sender: 'Marcus Green',
          preview: 'The client approved the revised scope.',
          timeLabel: '1 hour ago',
          href: '#',
          avatarInitials: 'MG',
          starred: false,
          tone: 'secondary',
        },
        {
          id: 'msg-003',
          sender: 'Nina Brooks',
          preview: 'Please assign this lead to the southeast team.',
          timeLabel: '3 hours ago',
          href: '#',
          avatarInitials: 'NB',
          starred: true,
          tone: 'warning',
        },
      ],
    });
  }),

  http.get(`${API_BASE}/notifications/summary/`, () => {
    return HttpResponse.json({
      unreadCount: 4,
      items: [
        {
          id: 'note-001',
          label: '4 new messages',
          timeLabel: '3 mins',
          href: '#',
          icon: 'message',
        },
        {
          id: 'note-002',
          label: '2 new lead assignments',
          timeLabel: '45 mins',
          href: '#',
          icon: 'people',
        },
        {
          id: 'note-003',
          label: '1 report export completed',
          timeLabel: '2 hours',
          href: '#',
          icon: 'report',
        },
        {
          id: 'note-004',
          label: 'System settings updated',
          timeLabel: '1 day',
          href: '#',
          icon: 'alert',
        },
      ],
    });
  }),

  http.get(`${API_BASE}/health/`, () => {
    return HttpResponse.json({
      status: 'ok',
      mode: 'mock',
    });
  }),

  http.get(`${API_BASE}/overview/`, () => {
  return HttpResponse.json({
    metrics: [
      {
        key: 'newLeads',
        label: 'Total New Leads',
        value: 8,
        helperText: 'Leads awaiting first action',
      },
      {
        key: 'qualifiedLeads',
        label: 'Total Qualified Leads',
        value: 12,
        helperText: 'Leads ready for quote activity',
      },
      {
        key: 'contactedLeads',
        label: 'Total Contacted Leads',
        value: 15,
        helperText: 'Leads with initial contact completed',
      },
      {
        key: 'activeLeads',
        label: 'Total Active Leads',
        value: 35,
        helperText: 'New, contacted, and qualified leads',
      },
    ],

    totalLeadsOverTime: [
      { label: 'Nov', totalLeads: 9, averageSalesPrice: 12800 },
      { label: 'Dec', totalLeads: 14, averageSalesPrice: 14250 },
      { label: 'Jan', totalLeads: 19, averageSalesPrice: 15800 },
      { label: 'Feb', totalLeads: 24, averageSalesPrice: 17100 },
      { label: 'Mar', totalLeads: 31, averageSalesPrice: 18900 },
      { label: 'Apr', totalLeads: 35, averageSalesPrice: 20400 },
    ],

    contactedLeadsOverTime: [
      { label: 'Nov', contactedLeads: 4, averageSalesPrice: 12100 },
      { label: 'Dec', contactedLeads: 6, averageSalesPrice: 13600 },
      { label: 'Jan', contactedLeads: 8, averageSalesPrice: 14900 },
      { label: 'Feb', contactedLeads: 10, averageSalesPrice: 16350 },
      { label: 'Mar', contactedLeads: 13, averageSalesPrice: 18200 },
      { label: 'Apr', contactedLeads: 15, averageSalesPrice: 19750 },
    ],
  });
}),
];