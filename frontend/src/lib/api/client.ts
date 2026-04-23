import { env } from '@/lib/config/env';
import { apiFetch } from '@/lib/utils/http';

function normalizePath(path: string) {
  return path.startsWith('/') ? path : `/${path}`;
}

export function buildApiPath(path: string) {
  return `${env.apiBaseUrl}${normalizePath(path)}`;
}

export function buildApiUrl(path: string, params?: URLSearchParams) {
  const url = new URL(buildApiPath(path), window.location.origin);
  if (params) {
    url.search = params.toString();
  }
  return url;
}

export async function getJson<T>(path: string, params?: URLSearchParams) {
  return apiFetch<T>(buildApiUrl(path, params));
}

export async function postJson<TResponse, TBody extends object>(path: string, body: TBody) {
  return apiFetch<TResponse>(buildApiUrl(path), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
}
