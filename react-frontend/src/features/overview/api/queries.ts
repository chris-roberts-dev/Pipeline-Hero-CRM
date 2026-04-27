import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../../lib/api/client';
import {
    tenantOverviewSchema,
    type TenantOverview,
} from '../schema';

export function useTenantOverviewQuery() {
  return useQuery({
    queryKey: ['tenant-overview'],
    queryFn: async (): Promise<TenantOverview> => {
      const data = await apiFetch<unknown>('/overview/');
      return tenantOverviewSchema.parse(data);
    },
  });
}