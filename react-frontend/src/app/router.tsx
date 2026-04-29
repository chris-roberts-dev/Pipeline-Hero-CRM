import { LeadDetailPage } from '@features/leads/pages/LeadDetailPage';
import { LeadsListPage } from '@features/leads/pages/LeadsListPage';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LoginRedirectPage } from '../features/auth/pages/LoginRedirectPage';
import { LandingPage } from '../features/landing/pages/LandingPage';
import { OverviewPage } from '../features/overview/pages/OverviewPage';
import { AppLayout } from './layouts/AppLayout';
import { PublicLayout } from './layouts/PublicLayout';


export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      {
        index: true,
        element: <LandingPage />,
      },
      {
        path: 'login',
        element: <LoginRedirectPage />,
      },
    ],
  },
  {
    path: 'app',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <OverviewPage />,
      },
    {
      path: 'leads',
      element: <LeadsListPage />,
    },
    {
      path: 'leads/:leadId',
      element: <LeadDetailPage />,
    },
      {
        path: '*',
        element: <Navigate to="/app" replace />,
      },
    ],
  },
]);