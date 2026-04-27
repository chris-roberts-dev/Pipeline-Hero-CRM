import { http, HttpResponse } from 'msw';
import {
    mockSession,
    unauthenticatedSession,
} from '../data/sessionFixtures';

const API_BASE = '/api/internal';

export const sessionHandlers = [
  http.get(`${API_BASE}/session/`, ({ request }) => {
    const url = new URL(request.url);
    const scenario = url.searchParams.get('scenario');

    if (scenario === 'logged-out') {
      return HttpResponse.json(unauthenticatedSession);
    }

    return HttpResponse.json(mockSession);
  }),
];