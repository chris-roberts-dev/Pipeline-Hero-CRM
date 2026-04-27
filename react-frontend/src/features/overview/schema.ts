import { z } from 'zod';

export const overviewMetricKeySchema = z.enum([
  'newLeads',
  'qualifiedLeads',
  'contactedLeads',
  'activeLeads',
]);

export const overviewMetricSchema = z.object({
  key: overviewMetricKeySchema,
  label: z.string(),
  value: z.number(),
  helperText: z.string(),
});

export const leadTrendPointSchema = z.object({
  label: z.string(),
  totalLeads: z.number(),
  averageSalesPrice: z.number(),
});

export const contactedLeadTrendPointSchema = z.object({
  label: z.string(),
  contactedLeads: z.number(),
  averageSalesPrice: z.number(),
});

export const tenantOverviewSchema = z.object({
  metrics: z.array(overviewMetricSchema),
  totalLeadsOverTime: z.array(leadTrendPointSchema),
  contactedLeadsOverTime: z.array(contactedLeadTrendPointSchema),
});

export type OverviewMetric = z.infer<typeof overviewMetricSchema>;
export type TenantOverview = z.infer<typeof tenantOverviewSchema>;
export type LeadTrendPoint = z.infer<typeof leadTrendPointSchema>;
export type ContactedLeadTrendPoint = z.infer<typeof contactedLeadTrendPointSchema>;