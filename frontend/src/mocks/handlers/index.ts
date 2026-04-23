import { organizationsHandlers } from '@/mocks/handlers/organizations';
import { messagesHandlers } from '@/mocks/handlers/messages';
import { notificationsHandlers } from '@/mocks/handlers/notifications';
import { sessionHandlers } from '@/mocks/handlers/session';

export const handlers = [
  ...sessionHandlers,
  ...messagesHandlers,
  ...notificationsHandlers,
  ...organizationsHandlers,
];
