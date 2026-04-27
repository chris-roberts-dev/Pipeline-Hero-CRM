import { type ReactNode, useMemo } from 'react';
import { Navigate } from 'react-router-dom';
import { useSessionQuery } from './api/queries';
import type { SessionBootstrap } from './schema';
import { SessionContext, type SessionContextValue } from './SessionContext';

type SessionProviderProps = {
  children: ReactNode;
};

export function SessionProvider({ children }: SessionProviderProps) {
  const sessionQuery = useSessionQuery();

  if (sessionQuery.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
          <p className="text-sm font-medium text-slate-900">Loading session...</p>
          <p className="mt-1 text-sm text-slate-500">
            Checking your organization access.
          </p>
        </div>
      </div>
    );
  }

  if (sessionQuery.isError || !sessionQuery.data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="max-w-md rounded-2xl border border-red-200 bg-white px-6 py-5 shadow-sm">
          <p className="text-sm font-medium text-red-700">
            Unable to load your session.
          </p>
          <p className="mt-1 text-sm text-slate-500">
            Refresh the page or sign in again.
          </p>
        </div>
      </div>
    );
  }

  if (!sessionQuery.data.isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <SessionContextBridge session={sessionQuery.data}>
      {children}
    </SessionContextBridge>
  );
}

type SessionContextBridgeProps = {
  session: SessionBootstrap;
  children: ReactNode;
};

function SessionContextBridge({
  session,
  children,
}: SessionContextBridgeProps) {
  const value = useMemo<SessionContextValue>(() => {
    const capabilityCodes = session.membership?.capabilityCodes ?? [];
    const roleNames = session.membership?.roleNames ?? [];

    return {
      session,
      hasCapability: (capability: string) =>
        capabilityCodes.includes(capability),
      hasRole: (role: string) => roleNames.includes(role),
    };
  }, [session]);

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
}