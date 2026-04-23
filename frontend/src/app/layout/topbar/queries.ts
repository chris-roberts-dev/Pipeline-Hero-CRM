import { queryOptions, useQuery } from '@tanstack/react-query';

import { getJson } from '@/lib/api/client';
import type { TopbarMessagesResponse, TopbarNotificationsResponse } from '@/app/layout/topbar/types';

async function fetchMessagesSummary(): Promise<TopbarMessagesResponse> {
  return getJson<TopbarMessagesResponse>('/messages/summary/');
}

async function fetchNotificationsSummary(): Promise<TopbarNotificationsResponse> {
  return getJson<TopbarNotificationsResponse>('/notifications/summary/');
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
