import type { QueryClient } from '@tanstack/react-query';
import { Navigate, Outlet, createBrowserRouter } from 'react-router-dom';

import { AuthRequiredPage } from '@/features/auth/components/AuthRequiredPage';
import { ProtectedLayout } from '@/features/auth/components/ProtectedLayout';
import { sessionQueryOptions } from '@/features/auth/queries/session';
import { OrganizationDetailPage } from '@/features/organizations/pages/OrganizationDetailPage';
import { OrganizationsListPage } from '@/features/organizations/pages/OrganizationsListPage';
import { TenantProvider } from '@/features/tenant/TenantContext';
import { LeadDetailPage } from '../features/leads/pages/LeadDetailPage';
import { LeadsListPage } from '../features/leads/pages/LeadsListPage';
import { OverviewPage } from '../features/overview/pages/OverviewPage';

function RootRoute() {
  return (
    <TenantProvider>
      <Outlet />
    </TenantProvider>
  );
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
              element: <OverviewPage />,
            },
            {
              path: 'organizations',
              element: <OrganizationsListPage />,
            },
            {
              path: 'organizations/:organizationId',
              element: <OrganizationDetailPage />,
            },
            {
              path: 'leads',
              element: <LeadsListPage />,
            },
            {
              path: 'leads/:leadId',
              element: <LeadDetailPage />,
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
