import { messagesHandlers } from '@/mocks/handlers/messages';
import { notificationsHandlers } from '@/mocks/handlers/notifications';
import { organizationsHandlers } from '@/mocks/handlers/organizations';
import { sessionHandlers } from '@/mocks/handlers/session';
import { leadsHandlers } from './leads';
import { overviewHandlers } from './overview';

export const handlers = [
  ...overviewHandlers,
  ...leadsHandlers,
  ...sessionHandlers,
  ...messagesHandlers,
  ...notificationsHandlers,
  ...organizationsHandlers,
];
