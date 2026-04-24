import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  CreateLeadPayload,
  Lead,
  LeadsListResponse,
  LeadStatus,
} from '../types';

const API_BASE = '/api/internal';

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function postJson<TResponse, TPayload>(
  path: string,
  payload: TPayload,
): Promise<TResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<TResponse>;
}

export type LeadsQueryParams = {
  search?: string;
  status?: LeadStatus | '';
};

export function useLeadsQuery(params: LeadsQueryParams = {}) {
  const searchParams = new URLSearchParams();

  if (params.search) {
    searchParams.set('search', params.search);
  }

  if (params.status) {
    searchParams.set('status', params.status);
  }

  const queryString = searchParams.toString();
  const path = queryString ? `/leads/?${queryString}` : '/leads/';

  return useQuery({
    queryKey: ['leads', params],
    queryFn: () => fetchJson<LeadsListResponse>(path),
  });
}

export function useLeadDetailQuery(leadId: string | undefined) {
  return useQuery({
    queryKey: ['leads', leadId],
    queryFn: () => fetchJson<Lead>(`/leads/${leadId}/`),
    enabled: Boolean(leadId),
  });
}

export function useCreateLeadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateLeadPayload) =>
      postJson<Lead, CreateLeadPayload>('/leads/', payload),

    onSuccess: (createdLead) => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.setQueryData(['leads', createdLead.id], createdLead);
    },
  });
}