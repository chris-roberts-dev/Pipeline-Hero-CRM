import { delay } from 'msw';

import { env } from '@/lib/config/env';
import { getMockScenarioFromCookieHeader } from '@/lib/dev/mockState';

export async function withMockDelay() {
  if (env.mockDelayMs > 0) {
    await delay(env.mockDelayMs);
  }
}

export function readScenarioFromRequest(request: Request) {
  return getMockScenarioFromCookieHeader(request.headers.get('cookie'));
}
