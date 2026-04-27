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
        path: '*',
        element: <Navigate to="/app" replace />,
      },
    ],
  },
]);