import type { OverviewResponse } from '../../features/overview/types';

export const mockOverview: OverviewResponse = {
  metrics: [
    {
      key: 'activeOrganizations',
      label: 'Total Active Organizations',
      value: 18,
      helperText: 'Organizations currently active',
    },
    {
      key: 'newLeads',
      label: 'Total New Leads',
      value: 6,
      helperText: 'Leads currently in New status',
    },
    {
      key: 'qualifiedLeads',
      label: 'Total Qualified Leads',
      value: 6,
      helperText: 'Leads ready for quote activity',
    },
    {
      key: 'contactedLeads',
      label: 'Total Contacted Leads',
      value: 5,
      helperText: 'Leads with initial contact completed',
    },
  ],

  leadsOverTime: [
    { label: 'Nov', value: 8 },
    { label: 'Dec', value: 11 },
    { label: 'Jan', value: 13 },
    { label: 'Feb', value: 15 },
    { label: 'Mar', value: 18 },
    { label: 'Apr', value: 20 },
  ],

  organizationsOverTime: [
    { label: 'Nov', value: 9 },
    { label: 'Dec', value: 10 },
    { label: 'Jan', value: 12 },
    { label: 'Feb', value: 14 },
    { label: 'Mar', value: 16 },
    { label: 'Apr', value: 18 },
  ],
};