import { queryOptions, useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../../lib/api/client';
import type {
    TopbarMessagesResponse,
    TopbarNotificationsResponse,
} from './types';

async function fetchMessagesSummary(): Promise<TopbarMessagesResponse> {
  return apiFetch<TopbarMessagesResponse>('/messages/summary/');
}

async function fetchNotificationsSummary(): Promise<TopbarNotificationsResponse> {
  return apiFetch<TopbarNotificationsResponse>('/notifications/summary/');
}

export const topbarMessagesQueryOptions = queryOptions({
  queryKey: ['topbar', 'messages'],
  queryFn: fetchMessagesSummary,
});

export const topbarNotificationsQueryOptions = queryOptions({
  queryKey: ['topbar', 'notifications'],
  queryFn: fetchNotificationsSummary,
});

export function useTopbarMessagesQuery() {
  return useQuery(topbarMessagesQueryOptions);
}

export function useTopbarNotificationsQuery() {
  return useQuery(topbarNotificationsQueryOptions);
}