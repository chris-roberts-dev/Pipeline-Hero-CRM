import { http, HttpResponse } from 'msw';
import { mockOverview } from '../data/overviewFixtures';

const API_BASE = '/api/internal';

export const overviewHandlers = [
  http.get(`${API_BASE}/overview/`, () => {
    return HttpResponse.json(mockOverview);
  }),
];