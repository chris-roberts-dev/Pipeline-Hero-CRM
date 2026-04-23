import {
  createContext,
  useContext,
  useMemo,
  type PropsWithChildren,
} from 'react';

import { useSessionQuery } from '@/features/auth/queries/session';
import type { OrganizationSummary, SessionBootstrap } from '@/lib/auth/types';

interface TenantContextValue {
  session: SessionBootstrap | null;
  organization: OrganizationSummary | null;
  capabilities: string[];
  hostSubdomain: string | null;
}

const TenantContext = createContext<TenantContextValue | null>(null);

function getHostSubdomain(hostname: string) {
  const parts = hostname.split('.');
  if (parts.length < 3) {
    return null;
  }

  return parts[0] ?? null;
}

export function TenantProvider({ children }: PropsWithChildren) {
  const { data } = useSessionQuery();

  const value = useMemo<TenantContextValue>(
    () => ({
      session: data ?? null,
      organization: data?.organization ?? null,
      capabilities: data?.capabilities ?? [],
      hostSubdomain: getHostSubdomain(window.location.hostname),
    }),
    [data],
  );

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within TenantProvider.');
  }

  return context;
}
