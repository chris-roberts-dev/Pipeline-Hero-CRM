import { Navigate } from 'react-router-dom';

import { LoadingScreen } from '@/components/ui/LoadingScreen';
import { useSessionQuery } from '@/features/auth/queries/session';
import { AppShell } from '@/app/layout/AppShell';

export function ProtectedLayout() {
  const { data, isPending } = useSessionQuery();

  if (isPending) {
    return <LoadingScreen message="Bootstrapping tenant session…" />;
  }

  if (!data?.authenticated || !data.organization || !data.user) {
    return <Navigate to="/auth/required" replace />;
  }

  return <AppShell />;
}
