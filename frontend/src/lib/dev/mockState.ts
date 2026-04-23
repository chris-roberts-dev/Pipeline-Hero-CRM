import { env } from '@/lib/config/env';

const STORAGE_KEY = 'mph:mock-scenario';
const COOKIE_KEY = 'mph_mock_scenario';

export type MockScenarioKey =
  | 'owner'
  | 'viewer'
  | 'impersonating'
  | 'logged-out'
  | 'organizations-empty'
  | 'organizations-error'
  | 'messages-empty'
  | 'messages-error'
  | 'notifications-empty'
  | 'notifications-error';

export const mockScenarioOptions: Array<{ value: MockScenarioKey; label: string }> = [
  { value: 'owner', label: 'Owner' },
  { value: 'viewer', label: 'Viewer' },
  { value: 'impersonating', label: 'Support impersonating' },
  { value: 'logged-out', label: 'Logged out' },
  { value: 'organizations-empty', label: 'Organizations empty' },
  { value: 'organizations-error', label: 'Organizations error' },
  { value: 'messages-empty', label: 'Messages empty' },
  { value: 'messages-error', label: 'Messages error' },
  { value: 'notifications-empty', label: 'Notifications empty' },
  { value: 'notifications-error', label: 'Notifications error' },
];

function isMockScenarioKey(value: string | null | undefined): value is MockScenarioKey {
  return mockScenarioOptions.some((option) => option.value === value);
}

function getCookieValue(name: string) {
  return document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`))
    ?.split('=')[1];
}

export function getMockScenario(): MockScenarioKey {
  const url = new URL(window.location.href);
  const fromQuery = url.searchParams.get('mockScenario');
  if (isMockScenarioKey(fromQuery)) {
    return fromQuery;
  }

  const fromCookie = getCookieValue(COOKIE_KEY);
  if (isMockScenarioKey(fromCookie)) {
    return fromCookie;
  }

  const fromStorage = window.localStorage.getItem(STORAGE_KEY);
  if (isMockScenarioKey(fromStorage)) {
    return fromStorage;
  }

  return isMockScenarioKey(env.mockScenario) ? env.mockScenario : 'owner';
}

export function setMockScenario(nextScenario: MockScenarioKey) {
  window.localStorage.setItem(STORAGE_KEY, nextScenario);
  document.cookie = `${COOKIE_KEY}=${nextScenario}; path=/; SameSite=Lax`;
}

export function getMockScenarioFromCookieHeader(cookieHeader: string | null | undefined): MockScenarioKey {
  const cookieMatch = cookieHeader
    ?.split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${COOKIE_KEY}=`))
    ?.split('=')[1];

  if (isMockScenarioKey(cookieMatch)) {
    return cookieMatch;
  }

  return isMockScenarioKey(env.mockScenario) ? env.mockScenario : 'owner';
}
