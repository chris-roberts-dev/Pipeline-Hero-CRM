import { queryOptions, useQuery } from '@tanstack/react-query';

import { getJson } from '@/lib/api/client';
import type { SessionBootstrap } from '@/lib/auth/types';
import { ApiError } from '@/lib/utils/http';

async function fetchSessionBootstrap(): Promise<SessionBootstrap> {
  try {
    return await getJson<SessionBootstrap>('/session/');
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return {
        authenticated: false,
        organization: null,
        user: null,
        capabilities: [],
        impersonation: {
          active: false,
          acting_as_email: null,
        },
      };
    }

    throw error;
  }
}

export const sessionQueryOptions = queryOptions({
  queryKey: ['session', 'bootstrap'],
  queryFn: fetchSessionBootstrap,
});

export function useSessionQuery() {
  return useQuery(sessionQueryOptions);
}
