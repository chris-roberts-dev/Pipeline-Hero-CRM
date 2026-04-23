const DEFAULT_API_BASE_URL = '/api/internal';
const DEFAULT_ROOT_LOGIN_URL = 'https://mypipelinehero.localhost:8443/';
const DEFAULT_MOCK_SCENARIO = 'owner';

function readBoolean(value: string | undefined, fallback = false) {
  if (value == null || value === '') {
    return fallback;
  }

  return value === 'true' || value === '1';
}

function readNumber(value: string | undefined, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL,
  rootLoginUrl: import.meta.env.VITE_ROOT_LOGIN_URL?.trim() || DEFAULT_ROOT_LOGIN_URL,
  enableApiMocks: readBoolean(import.meta.env.VITE_ENABLE_API_MOCKS, false),
  mockScenario: import.meta.env.VITE_MOCK_SCENARIO?.trim() || DEFAULT_MOCK_SCENARIO,
  mockDelayMs: readNumber(import.meta.env.VITE_MOCK_DELAY_MS, 150),
};
