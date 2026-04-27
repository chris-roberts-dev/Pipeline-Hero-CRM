import type { components } from '@/lib/api/generated/schema';

export type TopbarMessageItem = components['schemas']['TopbarMessageItem'];
export type TopbarMessagesResponse = components['schemas']['TopbarMessagesResponse'];
export type TopbarNotificationItem = components['schemas']['TopbarNotificationItem'];
export type TopbarNotificationsResponse = components['schemas']['TopbarNotificationsResponse'];

export type TopbarUserSummary = {
  displayName: string;
  email: string;
  roleLabel: string;
  memberSinceLabel: string;
  organizationName?: string | null;
  avatarInitials: string;
  profileHref?: string;
};
