import type { MockScenarioKey } from '@/lib/dev/mockState';
import type {
  TopbarMessageItem,
  TopbarMessagesResponse,
  TopbarNotificationItem,
  TopbarNotificationsResponse,
} from '@/app/layout/topbar/types';

const ownerMessages: TopbarMessageItem[] = [
  {
    id: 'msg_1',
    sender: 'Brad Diesel',
    preview: 'Call me whenever you can about the install schedule.',
    timeLabel: '4 hours ago',
    href: '#',
    avatarInitials: 'BD',
    starred: true,
    tone: 'danger',
  },
  {
    id: 'msg_2',
    sender: 'John Pierce',
    preview: 'I got your message. We are ready for the quote review.',
    timeLabel: '4 hours ago',
    href: '#',
    avatarInitials: 'JP',
    starred: true,
    tone: 'neutral',
  },
  {
    id: 'msg_3',
    sender: 'Nora Silvester',
    preview: 'The manufacturing estimate is ready for approval.',
    timeLabel: '1 day ago',
    href: '#',
    avatarInitials: 'NS',
    starred: true,
    tone: 'warning',
  },
];

const viewerMessages: TopbarMessageItem[] = [
  {
    id: 'msg_viewer_1',
    sender: 'Operations Desk',
    preview: 'Your read-only access was updated for this tenant.',
    timeLabel: '30 mins ago',
    href: '#',
    avatarInitials: 'OD',
    starred: false,
    tone: 'neutral',
  },
];

const impersonatingMessages: TopbarMessageItem[] = [
  {
    id: 'msg_support_1',
    sender: 'Bluebird Ops',
    preview: 'Please confirm whether support can review this quote issue.',
    timeLabel: '12 mins ago',
    href: '#',
    avatarInitials: 'BO',
    starred: true,
    tone: 'warning',
  },
  {
    id: 'msg_support_2',
    sender: 'Dispatch Team',
    preview: 'Work order 1042 needs a status update today.',
    timeLabel: '1 hour ago',
    href: '#',
    avatarInitials: 'DT',
    starred: false,
    tone: 'neutral',
  },
];

const ownerNotifications: TopbarNotificationItem[] = [
  {
    id: 'notif_1',
    label: '4 new messages',
    timeLabel: '3 mins',
    href: '#',
    icon: 'message',
  },
  {
    id: 'notif_2',
    label: '8 new member requests',
    timeLabel: '12 hours',
    href: '#',
    icon: 'people',
  },
  {
    id: 'notif_3',
    label: '3 new reports are ready',
    timeLabel: '2 days',
    href: '#',
    icon: 'report',
  },
];

const viewerNotifications: TopbarNotificationItem[] = [
  {
    id: 'notif_viewer_1',
    label: 'Permissions updated for your workspace',
    timeLabel: '15 mins',
    href: '#',
    icon: 'alert',
  },
];

const impersonatingNotifications: TopbarNotificationItem[] = [
  {
    id: 'notif_support_1',
    label: 'Support impersonation is active',
    timeLabel: 'Now',
    href: '#',
    icon: 'alert',
  },
  {
    id: 'notif_support_2',
    label: '2 task reminders are overdue',
    timeLabel: '18 mins',
    href: '#',
    icon: 'report',
  },
];

export function getMessagesFixture(scenario: MockScenarioKey): TopbarMessagesResponse {
  switch (scenario) {
    case 'viewer':
      return { unreadCount: viewerMessages.length, items: viewerMessages };
    case 'impersonating':
      return { unreadCount: impersonatingMessages.length, items: impersonatingMessages };
    case 'messages-empty':
      return { unreadCount: 0, items: [] };
    default:
      return { unreadCount: ownerMessages.length, items: ownerMessages };
  }
}

export function getNotificationsFixture(scenario: MockScenarioKey): TopbarNotificationsResponse {
  switch (scenario) {
    case 'viewer':
      return { unreadCount: viewerNotifications.length, items: viewerNotifications };
    case 'impersonating':
      return { unreadCount: impersonatingNotifications.length, items: impersonatingNotifications };
    case 'notifications-empty':
      return { unreadCount: 0, items: [] };
    default:
      return { unreadCount: ownerNotifications.length, items: ownerNotifications };
  }
}
