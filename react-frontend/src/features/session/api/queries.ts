import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../../lib/api/client';
import {
  sessionBootstrapSchema,
  type SessionBootstrap,
} from '../schema';

export function useSessionQuery() {
  return useQuery({
    queryKey: ['session'],
    queryFn: async (): Promise<SessionBootstrap> => {
      const data = await apiFetch<unknown>('/session/');
      return sessionBootstrapSchema.parse(data);
    },
    staleTime: 60_000,
    retry: false,
  });
}