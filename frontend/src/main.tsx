import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';

import { createAppRouter } from '@/app/router';
import { AppProviders } from '@/app/providers/AppProviders';
import { startMocking } from '@/mocks';
import { createQueryClient } from '@/lib/query/queryClient';
import '@/styles/index.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Could not find #root element.');
}

const queryClient = createQueryClient();
const router = createAppRouter(queryClient);

async function bootstrap() {
  await startMocking();

  createRoot(rootElement).render(
    <StrictMode>
      <AppProviders queryClient={queryClient}>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  );
}

void bootstrap();
