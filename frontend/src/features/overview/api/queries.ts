import { useQuery } from '@tanstack/react-query';
import type { OverviewResponse } from '../types';

const API_BASE = '/api/internal';

async function fetchOverview(): Promise<OverviewResponse> {
  const response = await fetch(`${API_BASE}/overview/`, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json() as Promise<OverviewResponse>;
}

export function useOverviewQuery() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: fetchOverview,
  });
}