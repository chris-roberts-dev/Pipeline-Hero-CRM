import { keepPreviousData, queryOptions, useQuery } from '@tanstack/react-query';

import { getJson } from '@/lib/api/client';
import type { components } from '@/lib/api/generated/schema';

export interface CompanyFilters {
  page: number;
  pageSize: number;
  search: string;
  status: 'all' | 'active' | 'inactive';
  ordering: 'updated_at' | '-updated_at' | 'name' | '-name';
}

export type CompanySummary = components['schemas']['CompanySummary'];
export type CompanyListResponse = components['schemas']['CompanyListResponse'];
export type CompanyCreateRequest = components['schemas']['CompanyCreateRequest'];

function buildCompaniesParams(filters: CompanyFilters) {
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

async function fetchCompanies(filters: CompanyFilters) {
  return getJson<CompanyListResponse>('/companies/', buildCompaniesParams(filters));
}

export function companiesQueryOptions(filters: CompanyFilters) {
  return queryOptions({
    queryKey: ['companies', filters],
    queryFn: () => fetchCompanies(filters),
    placeholderData: keepPreviousData,
  });
}

export function useCompaniesQuery(filters: CompanyFilters) {
  return useQuery(companiesQueryOptions(filters));
}
