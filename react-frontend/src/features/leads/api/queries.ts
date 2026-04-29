import {
    createLeadPayloadSchema,
    leadSchema,
    leadsListResponseSchema,
    type CreateLeadPayload,
    type Lead,
    type LeadSource,
    type LeadStatus,
    type LeadsListResponse,
} from '@features/leads/schema';
import { apiFetch } from '@lib/api/client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export type LeadsQueryParams = {
  search?: string;
  status?: LeadStatus | '';
  source?: LeadSource | '';
  ownerId?: string;
};

function buildLeadsQueryString(params: LeadsQueryParams) {
  const searchParams = new URLSearchParams();

  if (params.search) {
    searchParams.set('search', params.search);
  }

  if (params.status) {
    searchParams.set('status', params.status);
  }

  if (params.source) {
    searchParams.set('source', params.source);
  }

  if (params.ownerId) {
    searchParams.set('ownerId', params.ownerId);
  }

  return searchParams.toString();
}

export function useLeadsQuery(params: LeadsQueryParams = {}) {
  const queryString = buildLeadsQueryString(params);
  const path = queryString ? `/leads/?${queryString}` : '/leads/';

  return useQuery({
    queryKey: ['leads', 'list', params],
    queryFn: async (): Promise<LeadsListResponse> => {
      const data = await apiFetch<unknown>(path);
      return leadsListResponseSchema.parse(data);
    },
  });
}

export function useLeadDetailQuery(leadId: string | undefined) {
  return useQuery({
    queryKey: ['leads', 'detail', leadId],
    queryFn: async (): Promise<Lead> => {
      const data = await apiFetch<unknown>(`/leads/${leadId}/`);
      return leadSchema.parse(data);
    },
    enabled: Boolean(leadId),
  });
}

export function useCreateLeadMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateLeadPayload): Promise<Lead> => {
      const validatedPayload = createLeadPayloadSchema.parse(payload);

      const data = await apiFetch<unknown>('/leads/', {
        method: 'POST',
        body: JSON.stringify(validatedPayload),
      });

      return leadSchema.parse(data);
    },

    onSuccess: (createdLead) => {
      queryClient.invalidateQueries({
        queryKey: ['leads', 'list'],
      });

      queryClient.invalidateQueries({
        queryKey: ['tenant-overview'],
      });

      queryClient.setQueryData(
        ['leads', 'detail', createdLead.id],
        createdLead,
      );
    },
  });
}