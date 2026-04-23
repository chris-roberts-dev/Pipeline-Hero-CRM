import type { QueryClient } from '@tanstack/react-query';
import { Navigate, Outlet, createBrowserRouter } from 'react-router-dom';

import { AuthRequiredPage } from '@/features/auth/components/AuthRequiredPage';
import { ProtectedLayout } from '@/features/auth/components/ProtectedLayout';
import { sessionQueryOptions } from '@/features/auth/queries/session';
import { OrganizationsListPage } from '@/features/organizations/pages/OrganizationsListPage';
import { OrganizationDetailPage } from '@/features/organizations/pages/OrganizationDetailPage';
import { TenantProvider } from '@/features/tenant/TenantContext';

function RootRoute() {
  return (
    <TenantProvider>
      <Outlet />
    </TenantProvider>
  );
}

function DashboardRedirect() {
  return <Navigate to="/organizations" replace />;
}

function NotFoundPage() {
  return (
    <div className="standalone-page">
      <div className="standalone-page__card">
        <p className="ui-page-header__eyebrow">404</p>
        <h1>Page not found</h1>
        <p>The route exists outside the current scaffold. Add it when the next feature module is ready.</p>
      </div>
    </div>
  );
}

export function createAppRouter(queryClient: QueryClient) {
  return createBrowserRouter([
    {
      id: 'root',
      path: '/',
      loader: async () => queryClient.ensureQueryData(sessionQueryOptions),
      element: <RootRoute />,
      children: [
        {
          path: 'auth/required',
          element: <AuthRequiredPage />,
        },
        {
          element: <ProtectedLayout />,
          children: [
            {
              index: true,
              element: <DashboardRedirect />,
            },
            {
              path: 'organizations',
              element: <OrganizationsListPage />,
            },
            {
              path: 'organizations/:organizationId',
              element: <OrganizationDetailPage />,
            },
          ],
        },
      ],
    },
    {
      path: '*',
      element: <NotFoundPage />,
    },
  ]);
}
