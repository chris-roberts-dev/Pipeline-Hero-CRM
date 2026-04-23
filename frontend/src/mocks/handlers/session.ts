import { http, HttpResponse } from 'msw';

import { buildApiPath } from '@/lib/api/client';
import { getSessionFixture } from '@/mocks/data/sessionFixtures';
import { readScenarioFromRequest, withMockDelay } from '@/mocks/utils';

export const sessionHandlers = [
  http.get(buildApiPath('/session/'), async ({ request }) => {
    await withMockDelay();

    const scenario = readScenarioFromRequest(request);
    const session = getSessionFixture(scenario);

    if (!session) {
      return HttpResponse.json(
        { code: 'AUTH_REQUIRED', message: 'Authentication required.' },
        { status: 401 },
      );
    }

    return HttpResponse.json(session, { status: 200 });
  }),
];
