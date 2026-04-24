export type OverviewMetricKey =
  | 'activeOrganizations'
  | 'newLeads'
  | 'qualifiedLeads'
  | 'contactedLeads';

export type OverviewMetric = {
  key: OverviewMetricKey;
  label: string;
  value: number;
  helperText: string;
};

export type OverviewChartPoint = {
  label: string;
  value: number;
};

export type OverviewResponse = {
  metrics: OverviewMetric[];
  leadsOverTime: OverviewChartPoint[];
  organizationsOverTime: OverviewChartPoint[];
};