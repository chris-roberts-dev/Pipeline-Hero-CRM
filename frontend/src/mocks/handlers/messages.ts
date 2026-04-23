import { http, HttpResponse } from 'msw';

import { buildApiPath } from '@/lib/api/client';
import { getSessionFixture } from '@/mocks/data/sessionFixtures';
import { getMessagesFixture } from '@/mocks/data/topbarFixtures';
import { readScenarioFromRequest, withMockDelay } from '@/mocks/utils';

export const messagesHandlers = [
  http.get(buildApiPath('/messages/summary/'), async ({ request }) => {
    await withMockDelay();

    const scenario = readScenarioFromRequest(request);
    const session = getSessionFixture(scenario);
    if (!session) {
      return HttpResponse.json(
        { code: 'AUTH_REQUIRED', message: 'Authentication required.' },
        { status: 401 },
      );
    }

    if (scenario === 'messages-error') {
      return HttpResponse.json(
        { code: 'MOCK_FAILURE', message: 'Simulated messages endpoint failure.' },
        { status: 500 },
      );
    }

    return HttpResponse.json(getMessagesFixture(scenario), { status: 200 });
  }),
];
