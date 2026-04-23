import { http, HttpResponse } from 'msw';

import { buildApiPath } from '@/lib/api/client';
import { getSessionFixture } from '@/mocks/data/sessionFixtures';
import { getNotificationsFixture } from '@/mocks/data/topbarFixtures';
import { readScenarioFromRequest, withMockDelay } from '@/mocks/utils';

export const notificationsHandlers = [
  http.get(buildApiPath('/notifications/summary/'), async ({ request }) => {
    await withMockDelay();

    const scenario = readScenarioFromRequest(request);
    const session = getSessionFixture(scenario);
    if (!session) {
      return HttpResponse.json(
        { code: 'AUTH_REQUIRED', message: 'Authentication required.' },
        { status: 401 },
      );
    }

    if (scenario === 'notifications-error') {
      return HttpResponse.json(
        { code: 'MOCK_FAILURE', message: 'Simulated notifications endpoint failure.' },
        { status: 500 },
      );
    }

    return HttpResponse.json(getNotificationsFixture(scenario), { status: 200 });
  }),
];
