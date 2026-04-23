import { keepPreviousData, queryOptions, useQuery } from '@tanstack/react-query';

import { getJson } from '@/lib/api/client';
import type { components } from '@/lib/api/generated/schema';

export interface OrganizationFilters {
  page: number;
  pageSize: number;
  search: string;
  status: 'all' | 'active' | 'inactive';
  ordering: 'updated_at' | '-updated_at' | 'name' | '-name';
}

export type OrganizationSummary = components['schemas']['OrganizationSummary'];
export type OrganizationDetail = components['schemas']['OrganizationDetail'];
export type OrganizationListResponse = components['schemas']['OrganizationListResponse'];
export type OrganizationCreateRequest = components['schemas']['OrganizationCreateRequest'];

function buildOrganizationsParams(filters: OrganizationFilters) {
  const params = new URLSearchParams();
  params.set('page', String(filters.page));
  params.set('page_size', String(filters.pageSize));
  params.set('ordering', filters.ordering);

  if (filters.search) {
    params.set('search', filters.search);
  }

  if (filters.status !== 'all') {
    params.set('status', filters.status);
  }

  return params;
}

async function fetchOrganizations(filters: OrganizationFilters) {
  return getJson<OrganizationListResponse>('/organizations/', buildOrganizationsParams(filters));
}

async function fetchOrganizationDetail(organizationId: string) {
  return getJson<OrganizationDetail>(`/organizations/${organizationId}/`);
}

export function organizationsQueryOptions(filters: OrganizationFilters) {
  return queryOptions({
    queryKey: ['organizations', filters],
    queryFn: () => fetchOrganizations(filters),
    placeholderData: keepPreviousData,
  });
}

export function organizationDetailQueryOptions(organizationId: string) {
  return queryOptions({
    queryKey: ['organizations', 'detail', organizationId],
    queryFn: () => fetchOrganizationDetail(organizationId),
    enabled: Boolean(organizationId),
  });
}

export function useOrganizationsQuery(filters: OrganizationFilters) {
  return useQuery(organizationsQueryOptions(filters));
}

export function useOrganizationDetailQuery(organizationId: string) {
  return useQuery(organizationDetailQueryOptions(organizationId));
}
