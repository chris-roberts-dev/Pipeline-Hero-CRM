import { env } from '@/lib/config/env';
import { getMockScenario, setMockScenario } from '@/lib/dev/mockState';

export async function startMocking() {
  if (!env.enableApiMocks) {
    return;
  }

  setMockScenario(getMockScenario());

  try {
    const { worker } = await import('@/mocks/browser');
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: {
        url: '/mockServiceWorker.js',
      },
    });
  } catch (error) {
    console.warn('Failed to start API mocks. Run `npm run mocks:init` after install.', error);
  }
}
